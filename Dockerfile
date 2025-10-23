# 1. Base Image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Tambahkan user non-root
RUN adduser --disabled-password --gecos '' appuser

# 4. Copy file dependensi dan install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy seluruh kode aplikasi
COPY src/ ./src/

COPY publisher_bonus.py .

# --- Perbaikan Izin Volume ---
# 6. Buat folder /app/data SEKARANG (sebagai root)
RUN mkdir /app/data
# 7. BARU ubah kepemilikan /app DAN /app/data ke appuser
RUN chown -R appuser:appuser /app
# --- Akhir Perbaikan ---

# 8. Ganti ke user non-root
USER appuser

# 9. Expose port
EXPOSE 8080

# 10. Perintah untuk menjalankan aplikasi
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]