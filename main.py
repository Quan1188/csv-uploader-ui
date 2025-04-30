from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import pandas as pd
from io import StringIO
import unidecode

app = FastAPI()
# Cho phép frontend (Netlify) kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc chỉ Netlify domain của bạn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    # TODO: Xử lý hoặc ghi vào database ở đây
    return {"filename": file.filename, "columns": df.columns.tolist(), "rows": len(df)}
def get_connection():
    return psycopg2.connect(
        host="35.192.126.104",
        port=5432,
        dbname="vinatex_db",
        user="postgres",
        password="08102003"
    )

# ✅ Mapping các bảng
COLUMN_MAPPINGS = {
    "baocaobanhang": {
        "ngay_ban": "ngay",
        "ma_don_hang": "ma_don_hang",
        "ma_san_pham": "ma_san_pham",
        "ten_san_pham": "ten_san_pham",
        "so_luong_ban": "so_luong_ban",
        "gia_ban": "gia_ban",
        "doanh_thu": "doanh_thu",
        "khu_vuc": "khu_vuc",
        "kenh_ban_hang": "kenh_ban_hang",
        "phong_ban_gui": "phong_ban_gui"
    },
    "baocaonhansu": {
        "ngay": "ngay",
        "ma_nhan_vien": "ma_nv",
        "ten_nhan_vien": "ho_ten",
        "phong_ban": "phong_ban",
        "chuc_vu": "chuc_vu",
        "luong_ngay": "luong",
        "phu_cap": "phu_cap",
        "so_gio_lam_viec": "so_gio_lam_viec",
        "so_gio_tang_ca": "so_gio_tang_ca"
    },
    "baocaosanxuat": {
        "ngay_san_xuat": "ngay",
        "ma_lenh_san_xuat": "ma_lenh",
        "ma_san_pham": "ma_sp",
        "ten_san_pham": "ten_sp",
        "so_luong_ke_hoach": "so_luong_ke_hoach",
        "so_luong_thuc_te": "so_luong_thuc_te",
        "so_luong_loi": "so_luong_loi",
        "nha_may": "ten_nha_may",
        "trang_thai": "trang_thai"
    },
    "baocaokinhdoanh": {
        "nam": "nam",
        "thang": "thang",
        "mang_kinh_doanh": "mang_kinh_doanh",
        "tong_doanh_thu": "tong_doanh_thu",
        "loi_nhuan_gop": "loi_nhuan_gop",
        "chi_phi_ban_hang": "chi_phi_ban_hang",
        "chi_phi_quan_ly": "chi_phi_quan_ly",
        "loi_nhuan_truoc_thue": "loi_nhuan_truoc_thue",
        "loi_nhuan_sau_thue": "loi_nhuan_sau_thue",
        "ty_suat_loi_nhuan_gop": "ty_suat_loi_nhuan_gop",
        "ty_suat_loi_nhuan_rong": "ty_suat_loi_nhuan_rong",
        "tong_tai_san": "tong_tai_san",
        "tong_no_phai_tra": "tong_no_phai_tra",
        "von_chu_so_huu": "von_chu_so_huu",
        "he_so_no_von_chu_so_huu": "he_so_no_von_chu_so_huu",
        "he_so_thanh_toan_hien_hanh": "he_so_thanh_toan_hien_hanh",
        "luu_chuyen_tien_thuan_hd_kinh_doanh": "luu_chuyen_tien_thuan_hd_kinh_doanh",
        "luu_chuyen_dau_tu": "luu_chuyen_dau_tu",
        "luu_chuyen_tai_chinh": "luu_chuyen_tai_chinh",
        "tien_cuoi_ky": "tien_cuoi_ky",
        "vong_quay_hang_ton_kho": "vong_quay_hang_ton_kho",
        "ky_thu_tien_binh_quan": "ky_thu_tien_binh_quan",
        "roe": "roe",
        "roa": "roa"
    }
}

def normalize_column(col):
    return unidecode.unidecode(col.strip().lower().replace(" ", "_"))

@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        s = contents.decode('utf-8')
        df = pd.read_csv(StringIO(s))
        df.columns = [normalize_column(col) for col in df.columns]

        table_name = ""
        for key in COLUMN_MAPPINGS:
            if key in file.filename.lower():
                table_name = key
                break

        if not table_name:
            raise HTTPException(status_code=400, detail="Tên file không phù hợp, không xác định được bảng.")

        col_mapping = COLUMN_MAPPINGS[table_name]

        missing_cols = [col for col in col_mapping if col not in df.columns]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"Thiếu cột trong CSV: {missing_cols}")

        df = df[list(col_mapping.keys())]
        df.rename(columns=col_mapping, inplace=True)

        conn = get_connection()
        cur = conn.cursor()

        inserted = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                columns = ','.join([f'"{col}"' for col in row.index])
                placeholders = ','.join(['%s'] * len(row))
                sql = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'
                cur.execute(sql, tuple(row))
                inserted += 1
            except Exception as e:
                errors.append(f"Dòng {idx+1}: {e}")

        conn.commit()
        conn.close()

        if errors:
            return {
                "status": "partial_success",
                "table": table_name,
                "rows_inserted": inserted,
                "rows_failed": len(errors),
                "errors": errors[:10]
            }

        return {
            "status": "success",
            "table": table_name,
            "rows_inserted": inserted
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")