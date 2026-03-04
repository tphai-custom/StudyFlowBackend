from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import LibraryItem
from app.schemas.library import LibraryItemCreate

# ---------------------------------------------------------------------------
# v2 Seed data: 5 grades x 5 subjects = 25 records
# Each record has: grade, subject, title,
#   lessons[3], summaries[2], exercises[2], videos[2]
# ---------------------------------------------------------------------------

_V2_SEED: list[dict] = [
    # ============================== LOP 6 =====================================
    {
        "grade": 6, "subject": "toan", "title": "Lop 6 - Toan",
        "lessons": [
            "Chuong 1: Tap hop, so tu nhien va so nguyen",
            "Chuong 2: Phan so va cac phep tinh voi phan so",
            "Chuong 3: Hinh hoc phang - doan thang, goc, tam giac",
        ],
        "summaries": [
            "Tom tat cong thuc Toan 6 - So hoc & Phan so",
            "So do tu duy Hinh hoc Toan 6",
        ],
        "exercises": [
            "Bo 60 bai tap so hoc lop 6 (co dap an)",
            "De kiem tra hoc ky Toan 6 (5 de mau)",
        ],
        "videos": [
            "Playlist giai Toan 6 - Canh Dieu | YouTube",
            "Video on luyen Toan 6 - Ket noi tri thuc | YouTube",
        ],
        "tags": ["so tu nhien", "phan so", "hinh hoc", "lop 6"],
    },
    {
        "grade": 6, "subject": "ngu_van", "title": "Lop 6 - Ngu van",
        "lessons": [
            "Truyen dan gian: Thanh Giong, Son Tinh Thuy Tinh, Thach Sanh",
            "Van ban truyen ngan hien dai: Bai hoc duong doi dau tien",
            "Tieng Viet: Tu va cau tao tu tieng Viet",
        ],
        "summaries": [
            "Tom tat cot truyen cac tac pham Van 6",
            "Bang he thong nhan vat & chu de chuong trinh Van 6",
        ],
        "exercises": [
            "Bo de doc hieu Van 6 theo the loai (co huong dan)",
            "Bai tap tu vung & tu loai tieng Viet lop 6",
        ],
        "videos": [
            "Playlist phan tich tac pham Ngu van 6 | YouTube",
            "Video on tap Ngu van 6 - Co Nguyen Thi Lan | YouTube",
        ],
        "tags": ["truyen dan gian", "doc hieu", "tu vung", "lop 6"],
    },
    {
        "grade": 6, "subject": "tieng_anh", "title": "Lop 6 - Tieng Anh",
        "lessons": [
            "Unit 1-4: My new school, My home, My friends, My neighbourhood",
            "Unit 5-8: Natural wonders, Our Tet holiday, Television, Sports and games",
            "Ngu phap trong tam: thi hien tai don, hien tai tiep dien, can/cannot",
        ],
        "summaries": [
            "Bang tu vung trong tam theo tung Unit (lop 6)",
            "Tong hop ngu phap Tieng Anh 6 - bang tra nhanh",
        ],
        "exercises": [
            "Bo bai tap doc hieu va dien tu Tieng Anh 6 (co dap an)",
            "De kiem tra Tieng Anh 6 hoc ky I & II",
        ],
        "videos": [
            "Playlist hoc Tieng Anh 6 - Global Success | YouTube",
            "Video luyen Speaking & Listening Tieng Anh 6 | YouTube",
        ],
        "tags": ["vocabulary", "grammar", "reading", "lop 6"],
    },
    {
        "grade": 6, "subject": "lich_su", "title": "Lop 6 - Lich su",
        "lessons": [
            "Phan 1: Lich su the gioi co dai - Ai Cap, Luong Ha, Hy Lap, La Ma",
            "Phan 2: Lich su Viet Nam tu thoi nguyen thuy den the ky X",
            "Phan 3: Cac cuoc khoi nghia gianh doc lap (Hai Ba Trung, Ly Bi...)",
        ],
        "summaries": [
            "Nien bieu cac su kien & nhan vat Lich su lop 6",
            "So do tu duy Lich su Viet Nam tu co dai den the ky X",
        ],
        "exercises": [
            "100 cau trac nghiem Lich su 6 (co giai thich)",
            "Bo de tu luan Lich su 6 kem goi y tra loi",
        ],
        "videos": [
            "Playlist bai giang Lich su 6 - Canh Dieu | YouTube",
            "Video on tap su kien Lich su Viet Nam lop 6 | YouTube",
        ],
        "tags": ["co dai", "nguoi Viet co", "khoi nghia", "lop 6"],
    },
    {
        "grade": 6, "subject": "dia_li", "title": "Lop 6 - Dia li",
        "lessons": [
            "Chuong 1: Trai Dat - hinh dang, kich thuoc, cac chuyen dong",
            "Chuong 2: Bieu do, ban do va cach doc luoc do",
            "Chuong 3: Dia hinh, song ngoi, khi hau va tho nhuong",
        ],
        "summaries": [
            "Tom tat kien thuc Dia li 6 theo tung chuong",
            "Bang tra nhanh: cac khai niem Dia li 6",
        ],
        "exercises": [
            "Bai tap thuc hanh doc ban do & luoc do lop 6",
            "De kiem tra Dia li 6 - hoc ky I & II (co dap an)",
        ],
        "videos": [
            "Playlist video bai giang Dia li 6 | YouTube",
            "Video thuc hanh ky nang ban do lop 6 | YouTube",
        ],
        "tags": ["trai dat", "ban do", "dia hinh", "lop 6"],
    },
    # ============================== LOP 7 =====================================
    {
        "grade": 7, "subject": "toan", "title": "Lop 7 - Toan",
        "lessons": [
            "Chuong 1: So huu ti, so thuc va bai toan thuc te",
            "Chuong 2: Ham so va do thi - khai niem, ve do thi y = ax",
            "Chuong 3: Thong ke mo ta - bang, bieu do, so trung binh",
        ],
        "summaries": [
            "Tom tat ly thuyet Toan 7 - So hoc & Dai so",
            "So do tu duy Hinh hoc & Thong ke Toan 7",
        ],
        "exercises": [
            "Bo 70 bai tap Toan 7 co loi giai chi tiet",
            "5 de kiem tra hoc ky Toan 7 (kem dap an)",
        ],
        "videos": [
            "Playlist giai Toan 7 - Ket noi tri thuc | YouTube",
            "Video chuyen de Thong ke & Ham so lop 7 | YouTube",
        ],
        "tags": ["so huu ti", "ham so", "thong ke", "lop 7"],
    },
    {
        "grade": 7, "subject": "ngu_van", "title": "Lop 7 - Ngu van",
        "lessons": [
            "Tho tru tinh hien dai: Tieng ga trua, Ban den choi nha",
            "Van nghi luan: cach lap luan, dan chung, bo cuc bai van",
            "Tieng Viet: Cau dac biet, cau rut gon, lien ket doan van",
        ],
        "summaries": [
            "Tom tat & phan tich cac bai tho trong tam Van 7",
            "Huong dan viet van nghi luan xa hoi lop 7",
        ],
        "exercises": [
            "De doc hieu Ngu van 7 theo the loai (co goi y)",
            "Bai tap viet doan van nghi luan mau lop 7",
        ],
        "videos": [
            "Playlist phan tich tho Ngu van 7 | YouTube",
            "Video huong dan viet van nghi luan lop 7 | YouTube",
        ],
        "tags": ["tho", "nghi luan", "doc hieu", "lop 7"],
    },
    {
        "grade": 7, "subject": "tieng_anh", "title": "Lop 7 - Tieng Anh",
        "lessons": [
            "Unit 1-4: My hobbies, Health, Community service, Music",
            "Unit 5-8: Vietnam's traditions, An overcrowded world, Traffic, Films",
            "Ngu phap: thi qua khu don, so sanh hon/nhat, cau dieu kien loai 1",
        ],
        "summaries": [
            "Bang tu vung Unit 1-12 Tieng Anh 7 (cot nghia + phien am)",
            "Tom tat ngu phap trong tam lop 7 - bang so sanh",
        ],
        "exercises": [
            "Bo de luyen Reading + Writing Tieng Anh 7 (co dap an)",
            "Bai tap chuyen de ngu phap Tieng Anh 7",
        ],
        "videos": [
            "Playlist bai giang Tieng Anh 7 Global Success | YouTube",
            "Video luyen nghe Speaking Tieng Anh 7 | YouTube",
        ],
        "tags": ["past simple", "comparison", "conditional", "lop 7"],
    },
    {
        "grade": 7, "subject": "lich_su", "title": "Lop 7 - Lich su",
        "lessons": [
            "Phan 1: Lich su the gioi trung dai - phong kien Chau Au, Chau A",
            "Phan 2: Viet Nam thoi Bac thuoc lan 3 va cac trieu dai Ngo-Dinh-Tien Le",
            "Phan 3: Trieu dai Ly-Tran-Ho va cong cuoc chong ngoai xam",
        ],
        "summaries": [
            "Nien bieu Lich su lop 7 - tu the ky X den the ky XIV",
            "So do tu duy: Cac trieu dai phong kien Viet Nam",
        ],
        "exercises": [
            "120 cau trac nghiem Lich su 7 (co giai thich chi tiet)",
            "De tu luan Lich su 7 - hoc ky I & II",
        ],
        "videos": [
            "Playlist bai giang Lich su 7 | YouTube",
            "Video on tap trieu dai phong kien Viet Nam | YouTube",
        ],
        "tags": ["trung dai", "trieu dai", "Ly Tran", "lop 7"],
    },
    {
        "grade": 7, "subject": "dia_li", "title": "Lop 7 - Dia li",
        "lessons": [
            "Chuong 1: Moi truong va dan cu the gioi",
            "Chuong 2: Cac khu vuc dia li the gioi - Chau Phi, Chau My, Chau A",
            "Chuong 3: Dia li Dong Nam A - thien nhien, dan cu, kinh te",
        ],
        "summaries": [
            "Tom tat Dia li 7 - Moi truong & Dan cu",
            "Bang tra dac diem cac chau luc lop 7",
        ],
        "exercises": [
            "Bai tap thuc hanh Dia li 7 - bieu do & ban do",
            "De kiem tra Dia li 7 (co dap an)",
        ],
        "videos": [
            "Playlist video Dia li 7 - Ket noi tri thuc | YouTube",
            "Video chuyen de Dia li khu vuc lop 7 | YouTube",
        ],
        "tags": ["chau luc", "dan cu", "Dong Nam A", "lop 7"],
    },
    # ============================== LOP 8 =====================================
    {
        "grade": 8, "subject": "toan", "title": "Lop 8 - Toan",
        "lessons": [
            "Chuong 1: Phep nhan va phep chia da thuc - hang dang thuc dang nho",
            "Chuong 2: Phan thuc dai so - rut gon, cong, tru, nhan, chia",
            "Chuong 3: Hinh hoc - tu giac, dien tich, dinh ly Py-ta-go",
        ],
        "summaries": [
            "Tom tat 7 hang dang thuc dang nho & ung dung",
            "So do tu duy Hinh hoc Toan 8",
        ],
        "exercises": [
            "Bo 80 bai tap Dai so va Hinh hoc lop 8 (co loi giai)",
            "5 de thi hoc ky Toan 8 (co dap an chi tiet)",
        ],
        "videos": [
            "Playlist giai Toan 8 - Canh Dieu | YouTube",
            "Video chuyen de Hang dang thuc & Phan thuc lop 8 | YouTube",
        ],
        "tags": ["hang dang thuc", "phan thuc", "hinh hoc", "lop 8"],
    },
    {
        "grade": 8, "subject": "ngu_van", "title": "Lop 8 - Ngu van",
        "lessons": [
            "Van hoc hien thuc: Tat den (Ngo Tat To), Lao Hac (Nam Cao)",
            "Tho yeu nuoc dau the ky XX: Nho rung, Que huong, Khi con tu hú",
            "Tieng Viet: Tro tu, than tu, tinh thai tu, cau ghep",
        ],
        "summaries": [
            "Tom tat & phan tich tac pham van xuoi Ngu van 8",
            "Huong dan viet doan van nghi luan van hoc lop 8",
        ],
        "exercises": [
            "Bo de doc hieu Ngu van 8 - van xuoi & tho (co dap an)",
            "Bai tap Tieng Viet lop 8 - tro tu, cau ghep",
        ],
        "videos": [
            "Playlist phan tich tac pham Van 8 | YouTube",
            "Video on thi HK Ngu van 8 | YouTube",
        ],
        "tags": ["van hien thuc", "tho yeu nuoc", "cau ghep", "lop 8"],
    },
    {
        "grade": 8, "subject": "tieng_anh", "title": "Lop 8 - Tieng Anh",
        "lessons": [
            "Unit 1-4: Leisure activities, Life in the countryside, Peoples of Vietnam, Our customs",
            "Unit 5-8: Technology in our life, Folk tales, Pollution, English speaking countries",
            "Ngu phap: cau bi dong, reported speech, menh de quan he, cau dieu kien loai 2",
        ],
        "summaries": [
            "Bang tu vung Unit 1-12 Tieng Anh 8 (co nghia & vi du)",
            "Tom tat ngu phap trong tam lop 8 - passive vs active",
        ],
        "exercises": [
            "Bo bai tap Grammar chuyen de lop 8 (Passive, Reported Speech)",
            "De thi hoc ky Tieng Anh 8 - 5 de mau co dap an",
        ],
        "videos": [
            "Playlist hoc Tieng Anh 8 Global Success | YouTube",
            "Video luyen ngu phap Passive Voice lop 8 | YouTube",
        ],
        "tags": ["passive voice", "reported speech", "relative clauses", "lop 8"],
    },
    {
        "grade": 8, "subject": "lich_su", "title": "Lop 8 - Lich su",
        "lessons": [
            "Phan 1: Lich su the gioi can dai - Cach mang tu san, CMTS Phap",
            "Phan 2: Cac cuoc cach mang cong nghiep va chu nghia de quoc",
            "Phan 3: Viet Nam the ky XIX - thuc dan Phap xam luoc, phong trao khang chien",
        ],
        "summaries": [
            "Nien bieu Lich su lop 8 - the gioi & Viet Nam can dai",
            "So do tu duy phong trao yeu nuoc Viet Nam the ky XIX",
        ],
        "exercises": [
            "150 cau trac nghiem Lich su 8 (co giai thich)",
            "De thi hoc ky Lich su 8 (kem huong dan lam bai)",
        ],
        "videos": [
            "Playlist bai giang Lich su 8 | YouTube",
            "Video on tap Lich su Viet Nam the ky XIX | YouTube",
        ],
        "tags": ["can dai", "thuc dan Phap", "khang chien", "lop 8"],
    },
    {
        "grade": 8, "subject": "dia_li", "title": "Lop 8 - Dia li",
        "lessons": [
            "Chuong 1: Dia li chau A - tu nhien, dan cu, kinh te",
            "Chuong 2: Dia li cac khu vuc chau A - Dong A, Nam A, Tay Nam A",
            "Chuong 3: Viet Nam - vi tri dia li, dia hinh, khi hau",
        ],
        "summaries": [
            "Tom tat Dia li 8 - Chau A & Viet Nam tu nhien",
            "Bang tra dac diem dia hinh, khi hau Viet Nam lop 8",
        ],
        "exercises": [
            "Bai tap Dia li 8 - phan tich bieu do & so lieu",
            "De kiem tra Dia li 8 (co dap an)",
        ],
        "videos": [
            "Playlist video Dia li 8 | YouTube",
            "Video chuyen de Dia li tu nhien Viet Nam | YouTube",
        ],
        "tags": ["chau A", "Viet Nam tu nhien", "dia hinh", "lop 8"],
    },
    # ============================== LOP 9 =====================================
    {
        "grade": 9, "subject": "toan", "title": "Lop 9 - Toan",
        "lessons": [
            "Chuong 1: Can bac hai, can bac ba va he thuc luong da thuc",
            "Chuong 2: Ham so bac hai - do thi parabol, min/max",
            "Chuong 3: Hinh hoc khong gian - duong tron, goc o tam, dien tich quat",
        ],
        "summaries": [
            "Tom tat ly thuyet Toan 9 - So hoc & Dai so nang cao",
            "So do tu duy Hinh hoc Toan 9",
        ],
        "exercises": [
            "Bo 100 bai tap Toan 9 tuyen chon (co loi giai)",
            "De thi vao lop 10 mon Toan theo nam (2019-2024)",
        ],
        "videos": [
            "Playlist giai Toan 9 luyen thi vao lop 10 | YouTube",
            "Video chuyen de Can bac hai & Ham so bac hai | YouTube",
        ],
        "tags": ["can bac hai", "ham so bac hai", "luyen thi 10", "lop 9"],
    },
    {
        "grade": 9, "subject": "ngu_van", "title": "Lop 9 - Ngu van",
        "lessons": [
            "Truyen hien dai: Lang (Kim Lan), Lang le Sa Pa (Nguyen Thanh Long)",
            "Tho khang chien: Dong chi, Bai tho ve tieu doi xe khong kinh, Anh trang",
            "Tap lam van: Nghi luan van hoc - phan tich nhan vat, doan tho",
        ],
        "summaries": [
            "Tom tat & phan tich tac pham trong tam Van 9",
            "Huong dan viet bai nghi luan van hoc dang phan tich",
        ],
        "exercises": [
            "Bo de doc hieu Van 9 theo the loai (co huong dan chi tiet)",
            "Bai van mau phan tich nhan vat & doan tho lop 9",
        ],
        "videos": [
            "Playlist phan tich tac pham Ngu van 9 | YouTube",
            "Video on thi vao lop 10 mon Van | YouTube",
        ],
        "tags": ["van khang chien", "nghi luan", "luyen thi 10", "lop 9"],
    },
    {
        "grade": 9, "subject": "tieng_anh", "title": "Lop 9 - Tieng Anh",
        "lessons": [
            "Unit 1-4: Local environment, City life, English in the world, Life in the past",
            "Unit 5-8: Wonders of Vietnam, Viet Nam: then and now, Recipes, Tourism",
            "Ngu phap nang cao: wish sentences, phrasal verbs, complex sentences",
        ],
        "summaries": [
            "Bang tu vung Unit 1-12 Tieng Anh 9 (kem IPA)",
            "Tong hop ngu phap Tieng Anh 9 - menh de phuc, wish",
        ],
        "exercises": [
            "Bo de luyen thi vao lop 10 mon Tieng Anh (2019-2024)",
            "Bai tap Grammar chuyen de Tieng Anh 9 (co dap an)",
        ],
        "videos": [
            "Playlist on thi lop 10 Tieng Anh Global Success | YouTube",
            "Video luyen Writing Task lop 9 | YouTube",
        ],
        "tags": ["wish sentences", "phrasal verbs", "luyen thi 10", "lop 9"],
    },
    {
        "grade": 9, "subject": "lich_su", "title": "Lop 9 - Lich su",
        "lessons": [
            "Phan 1: Lich su the gioi hien dai sau 1945 - Chien tranh lanh, LHQ",
            "Phan 2: Viet Nam 1919-1945 - Dang CSVN ra doi, Cach mang thang Tam",
            "Phan 3: Khang chien chong Phap & My (1945-1975)",
        ],
        "summaries": [
            "Nien bieu Lich su Viet Nam hien dai lop 9",
            "So do tu duy cac giai doan khang chien 1945-1975",
        ],
        "exercises": [
            "200 cau trac nghiem Lich su 9 luyen thi vao lop 10",
            "De thi Lich su vao lop 10 theo tinh (2019-2024)",
        ],
        "videos": [
            "Playlist on thi Lich su vao lop 10 | YouTube",
            "Video tom tat Lich su Viet Nam 1945-1975 | YouTube",
        ],
        "tags": ["hien dai", "khang chien", "luyen thi 10", "lop 9"],
    },
    {
        "grade": 9, "subject": "dia_li", "title": "Lop 9 - Dia li",
        "lessons": [
            "Chuong 1: Dan cu va lao dong Viet Nam",
            "Chuong 2: Kinh te Viet Nam - nong nghiep, cong nghiep, dich vu",
            "Chuong 3: Dia li cac vung kinh te Viet Nam",
        ],
        "summaries": [
            "Tom tat Dia li 9 - Dan cu & Kinh te Viet Nam",
            "Bang tra nhanh so lieu kinh te - xa hoi Viet Nam",
        ],
        "exercises": [
            "Bai tap phan tich bieu do Dia li 9 (3 dang chinh)",
            "De thi Dia li vao lop 10 (co dap an)",
        ],
        "videos": [
            "Playlist on thi Dia li vao lop 10 | YouTube",
            "Video chuyen de Dia li cac vung kinh te Viet Nam | YouTube",
        ],
        "tags": ["dan cu", "kinh te Viet Nam", "luyen thi 10", "lop 9"],
    },
    # ============================== LOP 10 ====================================
    {
        "grade": 10, "subject": "toan", "title": "Lop 10 - Toan",
        "lessons": [
            "Chuong 1: Menh de - Tap hop - Ham so va do thi bac nhat, bac hai",
            "Chuong 2: Bat phuong trinh va he bat phuong trinh bac nhat hai an",
            "Chuong 3: Vec-to trong mat phang va ung dung hinh hoc",
        ],
        "summaries": [
            "Tom tat ly thuyet Dai so lop 10 - Ham so & Bat phuong trinh",
            "So do tu duy Hinh hoc & Vecto lop 10",
        ],
        "exercises": [
            "Bo 100 bai tap Toan 10 co loi giai (Dai so & Hinh hoc)",
            "De kiem tra chuong Toan 10 - hoc ky I & II",
        ],
        "videos": [
            "Playlist giai Toan 10 - Ket noi tri thuc | YouTube",
            "Video chuyen de Ham so & Vecto lop 10 | YouTube",
        ],
        "tags": ["ham so", "bat phuong trinh", "vecto", "lop 10"],
    },
    {
        "grade": 10, "subject": "ngu_van", "title": "Lop 10 - Ngu van",
        "lessons": [
            "Van hoc dan gian: Su thi Dam San, ca dao, tuc ngu, truyen co tich",
            "Van hoc trung dai: Dai cao binh Ngo, Truyen Kieu - doan trich",
            "Tap lam van: Nghi luan van hoc & nghi luan xa hoi THPT",
        ],
        "summaries": [
            "Tom tat & phan tich tac pham van hoc trong tam lop 10",
            "Huong dan viet bai nghi luan THPT - dan y chuan",
        ],
        "exercises": [
            "Bo de doc hieu Van 10 theo the loai (co goi y)",
            "Van mau nghi luan xa hoi & phan tich tac pham lop 10",
        ],
        "videos": [
            "Playlist phan tich tac pham Ngu van 10 | YouTube",
            "Video on tap Ngu van 10 - Co Ha Huong | YouTube",
        ],
        "tags": ["van dan gian", "van trung dai", "Truyen Kieu", "lop 10"],
    },
    {
        "grade": 10, "subject": "tieng_anh", "title": "Lop 10 - Tieng Anh",
        "lessons": [
            "Unit 1-4: Family life, Your body and you, Music, For a better community",
            "Unit 5-8: Inventions, Gender equality, Cultural diversity, New ways to learn",
            "Ngu phap: Perfect tenses, gerunds vs infinitives, cau dieu kien loai 3",
        ],
        "summaries": [
            "Bang tu vung trong tam Tieng Anh 10 theo chu de",
            "Tong hop ngu phap Tieng Anh 10 - Perfect Tenses & Conditionals",
        ],
        "exercises": [
            "Bo bai tap Tieng Anh 10 - Grammar & Vocabulary (co dap an)",
            "De kiem tra hoc ky Tieng Anh 10 (5 de mau)",
        ],
        "videos": [
            "Playlist bai giang Tieng Anh 10 Global Success | YouTube",
            "Video luyen Writing & Speaking Tieng Anh 10 | YouTube",
        ],
        "tags": ["perfect tenses", "conditionals", "vocabulary", "lop 10"],
    },
    {
        "grade": 10, "subject": "lich_su", "title": "Lop 10 - Lich su",
        "lessons": [
            "Phan 1: Lich su the gioi tu nguon goc den the ky XV",
            "Phan 2: Viet Nam tu nguon goc den the ky X - Van Lang, Au Lac",
            "Phan 3: Dat nuoc thoi Ly-Tran-Le So (the ky XI-XV)",
        ],
        "summaries": [
            "Nien bieu Lich su lop 10 - the gioi & Viet Nam co trung dai",
            "So do tu duy Van hoa & Kinh te thoi phong kien Viet Nam",
        ],
        "exercises": [
            "150 cau trac nghiem Lich su 10 (co giai thich)",
            "De kiem tra hoc ky Lich su 10 (kem dap an)",
        ],
        "videos": [
            "Playlist bai giang Lich su 10 | YouTube",
            "Video on tap Lich su Viet Nam co trung dai | YouTube",
        ],
        "tags": ["co dai", "Van Lang", "Le So", "lop 10"],
    },
    {
        "grade": 10, "subject": "dia_li", "title": "Lop 10 - Dia li",
        "lessons": [
            "Chuong 1: Vu tru - He Mat Troi, Trai Dat va cac he qua",
            "Chuong 2: Dia li dan cu - dan so, do thi hoa, di dan",
            "Chuong 3: Dia li kinh te - nong nghiep, cong nghiep, dich vu toan cau",
        ],
        "summaries": [
            "Tom tat Dia li 10 - Tu nhien & Dan cu the gioi",
            "Bang tra cac chi so dia li kinh te - xa hoi the gioi",
        ],
        "exercises": [
            "Bai tap phan tich bieu do Dia li 10 (5 dang bieu do can biet)",
            "De kiem tra hoc ky Dia li 10 (co huong dan lam bai)",
        ],
        "videos": [
            "Playlist bai giang Dia li 10 | YouTube",
            "Video chuyen de Dia li kinh te - xa hoi lop 10 | YouTube",
        ],
        "tags": ["vu tru", "dan so", "kinh te the gioi", "lop 10"],
    },
]

# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

async def list_library(db: AsyncSession, owner_user_id: str) -> list[LibraryItem]:
    """Return system-shared items + user's own items."""
    result = await db.execute(
        select(LibraryItem)
        .where(or_(LibraryItem.owner_user_id.is_(None), LibraryItem.owner_user_id == owner_user_id))
        .order_by(LibraryItem.grade, LibraryItem.subject, LibraryItem.title)
    )
    return list(result.scalars().all())


async def search_library(
    db: AsyncSession,
    owner_user_id: str,
    query: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    resource_type: Optional[str] = None,
) -> list[LibraryItem]:
    conditions = [or_(LibraryItem.owner_user_id.is_(None), LibraryItem.owner_user_id == owner_user_id)]
    if subject:
        conditions.append(LibraryItem.subject == subject)
    if grade:
        conditions.append(LibraryItem.grade == grade)
    if resource_type:
        conditions.append(LibraryItem.resource_type == resource_type)

    stmt = (
        select(LibraryItem)
        .where(and_(*conditions))
        .order_by(LibraryItem.grade, LibraryItem.subject, LibraryItem.title)
    )
    items = list((await db.execute(stmt)).scalars().all())

    if query:
        q = query.lower()
        items = [
            item for item in items
            if q in " ".join([
                item.title or "",
                item.summary or "",
                " ".join(item.tags or []),
                " ".join(item.lessons or []),
                " ".join(item.summaries or []),
                " ".join(item.exercises or []),
                " ".join(item.videos or []),
            ]).lower()
        ]
    return items


# ---------------------------------------------------------------------------
# v2 List / Search (system-only, no user scope needed)
# ---------------------------------------------------------------------------

async def list_library_v2(
    db: AsyncSession,
    grade: Optional[int] = None,
    subject: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[LibraryItem]:
    """Return system library v2 items filtered by grade/subject/keyword."""
    conditions: list = [
        LibraryItem.owner_user_id.is_(None),
        LibraryItem.lessons.isnot(None),
    ]
    if grade is not None:
        conditions.append(LibraryItem.grade == grade)
    if subject:
        conditions.append(LibraryItem.subject == subject)

    stmt = (
        select(LibraryItem)
        .where(and_(*conditions))
        .order_by(LibraryItem.grade, LibraryItem.subject)
        .limit(limit)
        .offset(offset)
    )
    items = list((await db.execute(stmt)).scalars().all())

    if q:
        kw = q.lower()
        items = [
            item for item in items
            if kw in " ".join([
                item.title or "",
                " ".join(item.lessons or []),
                " ".join(item.summaries or []),
                " ".join(item.exercises or []),
                " ".join(item.videos or []),
                " ".join(item.tags or []),
            ]).lower()
        ]
    return items


# ---------------------------------------------------------------------------
# v2 Upsert seed
# ---------------------------------------------------------------------------

async def upsert_seed_library_v2(
    db: AsyncSession,
    grades: list[int],
    subjects: list[str],
) -> dict:
    """Upsert v2 seed records for the given grades/subjects subset."""
    inserted = 0
    updated = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    subset = [
        rec for rec in _V2_SEED
        if rec["grade"] in grades and rec["subject"] in subjects
    ]

    for rec in subset:
        result = await db.execute(
            select(LibraryItem).where(
                and_(
                    LibraryItem.grade == rec["grade"],
                    LibraryItem.subject == rec["subject"],
                    LibraryItem.owner_user_id.is_(None),
                    LibraryItem.lessons.isnot(None),
                )
            )
        )
        existing: Optional[LibraryItem] = result.scalar_one_or_none()

        if existing:
            existing.title = rec["title"]
            existing.lessons = rec["lessons"]
            existing.summaries = rec["summaries"]
            existing.exercises = rec["exercises"]
            existing.videos = rec["videos"]
            existing.tags = rec["tags"]
            existing.updated_at = now
            updated += 1
        else:
            item = LibraryItem(
                id=str(uuid.uuid4()),
                subject=rec["subject"],
                grade=rec["grade"],
                level=f"Lop {rec['grade']}",
                title=rec["title"],
                summary=f"{rec['title']} - tai lieu he thong",
                resource_type="lesson",
                lessons=rec["lessons"],
                summaries=rec["summaries"],
                exercises=rec["exercises"],
                videos=rec["videos"],
                tags=rec["tags"],
                owner_user_id=None,
                created_by="system",
                created_at=now,
                updated_at=now,
            )
            db.add(item)
            inserted += 1

    await db.flush()
    return {"inserted_count": inserted, "updated_count": updated, "skipped_count": skipped}


# ---------------------------------------------------------------------------
# Legacy per-item seed (kept for /library/seed endpoint)
# ---------------------------------------------------------------------------

async def save_library_items(
    db: AsyncSession,
    items: list[LibraryItemCreate],
    owner_user_id: Optional[str] = None,
) -> list[LibraryItem]:
    saved = []
    for payload in items:
        data = payload.model_dump()
        item = LibraryItem(id=str(uuid.uuid4()), **data, owner_user_id=owner_user_id)
        db.add(item)
        saved.append(item)
    await db.flush()
    return saved


async def seed_library(db: AsyncSession) -> int:
    """Legacy seed (no-op if already seeded)."""
    existing = await db.execute(
        select(LibraryItem).where(LibraryItem.created_by == "system").limit(1)
    )
    if existing.scalar_one_or_none():
        return 0
    result = await upsert_seed_library_v2(db, list(range(6, 11)), ["toan", "ngu_van", "tieng_anh", "lich_su", "dia_li"])
    return result["inserted_count"]


async def reseed_library(db: AsyncSession) -> int:
    """Delete all system items and re-seed."""
    await db.execute(delete(LibraryItem).where(LibraryItem.created_by == "system"))
    await db.flush()
    result = await upsert_seed_library_v2(db, list(range(6, 11)), ["toan", "ngu_van", "tieng_anh", "lich_su", "dia_li"])
    return result["inserted_count"]