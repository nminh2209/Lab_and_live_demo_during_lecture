# Codebase - MediLich Prototype

Thu muc nay chua toan bo code prototype Day 06.

## Chay nhanh

```powershell
cd codebase\prototype\server
copy .env.example .env
# Dien OPENAI_API_KEY vao .env neu demo live AI
npm install
npm start
```

Mo `http://localhost:3000`.

## Che do demo

- Co API key: upload anh don thuoc de goi AI Vision/parse that.
- Khong co API key: dung fixture trong app de demo cac duong happy, low-confidence va risky/failure.
- VietOCR tuy chon: chay `python vietocr_service.py` trong `codebase\prototype\server`, sau do dat `OCR_MODE=auto` va `VIETOCR_URL=http://127.0.0.1:5001` trong `.env`.

## Cau truc

```text
prototype/
├── index.html
├── css/
├── js/
├── data/
├── fixtures/
└── server/
```

`codebase/data/` chua du lieu MOH registry phuc vu badge doi chieu thuoc trong demo.

Khong commit `.env`, `node_modules/` hoac log runtime.
