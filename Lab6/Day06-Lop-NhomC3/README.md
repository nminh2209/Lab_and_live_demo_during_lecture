# Day06-Lop-NhomC3 - MediLich

MediLich la prototype Healthcare giup nguoi benh hoac nguoi nha chuyen anh/PDF don thuoc thanh lich uong thuoc co the xac nhan, kem the thong tin thuoc bang tieng Viet. AI tham gia o vai tro augmentation: doc don, trich xuat thuoc-lieu-tan suat, goi y lich va thong tin thuoc; nguoi dung luon xac nhan/chinh sua truoc khi luu.

## Thanh vien

| Ma hoc vien | Ho va ten | Vai tro chinh |
|---|---|---|
| 2A202600963 | Nguyen Hoang Minh | Backend, OCR va AI parse |
| 2A202600601 | Luong Quoc Dung | Frontend va UX prototype |
| 2A202600774 | Hoang Khuong Duy | Research, evidence va QA failure path |
| 2A202600716 | Cu Tien Nam | SPEC, noi dung thuoc va demo script |

## Phan cong cong viec

| Thanh vien | Phu trach | Artifact |
|---|---|---|
| Nguyen Hoang Minh | OpenAI Vision/parse, VietOCR optional, API backend | `codebase/prototype/server/`, `codebase/prototype/fixtures/`, `codebase/prototype/js/api.js`, `codebase/prototype/js/parse.js` |
| Luong Quoc Dung | Giao dien Android web, upload/review/lich/the thuoc | `codebase/prototype/index.html`, `codebase/prototype/css/styles.css`, `codebase/prototype/js/app.js` |
| Hoang Khuong Duy | Bang chung, test duong loi va guardrail | `spec/evidence-pack.md`, `evidences/`, fixture risky/low-confidence |
| Cu Tien Nam | SPEC, synthesis, drug cards va kich ban demo | `spec/spec.md`, `spec/synthesis-decide-toolkit.md`, `codebase/prototype/data/drugs.json`, `codebase/prototype/demo-script.md` |

## Cau truc nop bai

```text
Day06-Lop-NhomC3/
├── README.md
├── spec/
│   ├── spec.md
│   ├── evidence-pack.md
│   └── synthesis-decide-toolkit.md
└── codebase/
    ├── README.md
    ├── data/
    └── prototype/
        ├── index.html
        ├── css/
        ├── js/
        ├── data/
        ├── fixtures/
        └── server/
```

## Cach chay prototype

```powershell
cd codebase\prototype\server
copy .env.example .env
# Dien OPENAI_API_KEY vao .env neu muon demo AI live
npm install
npm start
```

Mo `http://localhost:3000`.

Neu khong co API key hoac mat mang, mo app va dung tab Demo/fixture de chay happy case, low-confidence case va risky/failure case.

## Cong cu va API da dung

- Frontend: Vanilla JavaScript ES Modules, HTML, CSS.
- Backend: Node.js, Express, multer.
- AI/OCR: OpenAI-compatible API cho Vision/parse JSON; ho tro Gemini OpenAI-compatible base URL qua env.
- OCR tuy chon: VietOCR Python Flask service.
- Data/demo: local fixtures, `data/drugs.json` va du lieu registry trong `codebase/data/`.
- Lookup/phu tro: Vinmec citation lookup, MOH registry demo data, OpenStreetMap Overpass cho nha thuoc/benh vien gan.

## Demo slice

Nguoi dung upload anh don thuoc in/digital, AI trich xuat danh sach thuoc, man hinh Review bat buoc hien confidence/warning, nguoi dung sua neu can roi luu lich uong. Tab Thuoc hien the thong tin thuoc, citation va badge doi chieu danh muc; tab Lich/Nhac hien cac lan uong trong ngay.
