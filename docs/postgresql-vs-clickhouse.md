# PostgreSQL vs ClickHouse — So sánh chi tiết về kiến trúc và hiệu năng

## Mục lục

- [1. OLTP vs OLAP](#1-oltp-vs-olap)
- [2. Row Storage vs Column Storage](#2-row-storage-vs-column-storage)
- [3. Data Compression](#3-data-compression)
- [4. Vectorized Execution vs Volcano Model](#4-vectorized-execution-vs-volcano-model)
- [5. CPU Cache Efficiency](#5-cpu-cache-efficiency)
- [6. B-Tree Index vs Sparse Index](#6-b-tree-index-vs-sparse-index)
- [7. Random I/O vs Sequential I/O](#7-random-io-vs-sequential-io)
- [8. Parallel Processing](#8-parallel-processing)
- [9. MVCC Overhead](#9-mvcc-overhead)
- [10. Tổng hợp benchmark](#10-tổng-hợp-benchmark)
- [11. Khi nào dùng gì?](#11-khi-nào-dùng-gì)

---

## 1. OLTP vs OLAP

### 1.1 Định nghĩa

- **OLTP** (Online Transaction Processing): Xử lý giao dịch thời gian thực, phục vụ **vận hành hàng ngày**.
- **OLAP** (Online Analytical Processing): Xử lý phân tích dữ liệu lớn, phục vụ **ra quyết định kinh doanh**.

PostgreSQL được thiết kế cho OLTP. ClickHouse được thiết kế cho OLAP.

### 1.2 Ví dụ thực tế

Một cửa hàng thương mại điện tử:

**OLTP** — hệ thống chạy khi khách đặt hàng:

- Khách thêm sản phẩm vào giỏ
- Khách thanh toán -> trừ tiền ví -> tạo đơn hàng -> giảm tồn kho
- Cập nhật trạng thái đơn: "đang giao"
- Khách hủy đơn -> hoàn tiền -> cộng lại tồn kho

**OLAP** — hệ thống khi chủ shop xem báo cáo:

- Tháng này doanh thu bao nhiêu?
- Sản phẩm nào bán chạy nhất Q1?
- So sánh doanh thu Hà Nội vs Sài Gòn theo từng tháng
- Dự đoán xu hướng bán hàng 3 tháng tới

### 1.3 So sánh

| Tiêu chí | OLTP | OLAP |
|---|---|---|
| **Mục đích** | Vận hành, giao dịch | Phân tích, báo cáo |
| **Người dùng** | Nhân viên, khách hàng, app | Quản lý, analyst, data team |
| **Kiểu query** | INSERT, UPDATE, DELETE đơn lẻ | SELECT phức tạp, GROUP BY, JOIN lớn |
| **Dữ liệu truy cập** | Vài row mỗi lần | Hàng triệu đến hàng tỷ rows mỗi lần |
| **Tốc độ yêu cầu** | Milliseconds (phải nhanh) | Seconds đến minutes (chấp nhận được) |
| **Tần suất** | Hàng nghìn query/giây | Vài query/phút hoặc /giờ |
| **Data model** | Normalized (3NF) — chia nhiều bảng | Denormalized (Star/Snowflake schema) |
| **Ưu tiên** | Tính toàn vẹn (ACID) | Tốc độ đọc, throughput |

### 1.4 Data Model khác nhau

**OLTP — Normalized** (tách nhỏ, tránh trùng lặp):

```
users:        [id, name, email]
orders:       [id, user_id, created_at, status]
order_items:  [id, order_id, product_id, qty, price]
products:     [id, name, category_id]
categories:   [id, name]
```

Cần JOIN 5 bảng để lấy "khách A mua gì", nhưng UPDATE rất dễ — sửa 1 chỗ là xong.

**OLAP — Denormalized** (gộp lại, chấp nhận trùng lặp):

```
fact_sales: [
  date, user_name, user_city,
  product_name, category_name,
  quantity, revenue
]
```

Mọi thứ nằm trong 1 bảng, không cần JOIN. Câu query `SELECT SUM(revenue) GROUP BY category_name` chạy cực nhanh.

### 1.5 ACID vs BASE

**OLTP cần ACID:**

```sql
-- Chuyển 100k từ ví A sang ví B
BEGIN TRANSACTION;
  UPDATE wallets SET balance = balance - 100000 WHERE user = 'A';
  UPDATE wallets SET balance = balance + 100000 WHERE user = 'B';
COMMIT;
```

Hoặc cả hai thành công, hoặc cả hai rollback. Không bao giờ xảy ra mất tiền giữa chừng.

**OLAP chấp nhận BASE** (Eventually Consistent):

- Báo cáo doanh thu có thể chậm vài phút so với thực tế
- Dữ liệu "gần đúng" là đủ tốt cho phân tích
- Ưu tiên tốc độ đọc hơn tính chính xác tuyệt đối

### 1.6 Kiến trúc tổng thể

```
                    ┌──────────────┐
  Users/App ──────> │  OLTP (PG)   │
                    │  PostgreSQL  │
                    │  MySQL       │
                    └──────┬───────┘
                           │
                      ETL / CDC
                    (Extract, Transform, Load)
                           │
                    ┌──────v───────┐
  Analysts ───────> │  OLAP (DW)   │
  BI Tools          │  ClickHouse  │
                    │  BigQuery    │
                    │  Redshift    │
                    └──────────────┘
```

OLTP thu thập dữ liệu giao dịch. ETL pipeline chuyển dữ liệu sang data warehouse. OLAP phục vụ phân tích trên dữ liệu đã tổng hợp.

---

## 2. Row Storage vs Column Storage

Đây là sự khác biệt **cốt lõi** về kiến trúc giữa PostgreSQL và ClickHouse.

### 2.1 PostgreSQL — Row-oriented storage

Mỗi page (8KB) chứa nhiều row liền nhau trên disk:

```
Page 1 (8KB):
┌───────────────────────────────────────────────────────────┐
│ Row1: [id=1, name="Nguyen Van A", age=25, city="HN", salary=15000000] │
│ Row2: [id=2, name="Tran Thi B",  age=30, city="SG", salary=20000000] │
│ Row3: [id=3, name="Le Van C",    age=22, city="DN", salary=12000000] │
└───────────────────────────────────────────────────────────┘
```

Khi chạy query `SELECT AVG(salary) FROM employees` trên 100 triệu rows:

- PostgreSQL phải đọc **toàn bộ page** từ disk
- Mỗi row ~100 bytes, nhưng chỉ cần cột `salary` (8 bytes)
- **Lãng phí ~92% I/O** — đọc name, city, age... rồi vứt đi

### 2.2 ClickHouse — Column-oriented storage

Mỗi cột lưu trong **file riêng biệt** trên disk:

```
id.bin:     [1, 2, 3, 4, 5, ...]
name.bin:   ["Nguyen Van A", "Tran Thi B", ...]
age.bin:    [25, 30, 22, 28, 35, ...]
salary.bin: [15M, 20M, 12M, 18M, 25M, ...]
```

Khi chạy query `SELECT AVG(salary)`:

- Chỉ đọc file `salary.bin`
- **100% dữ liệu đọc lên đều hữu ích**, không lãng phí byte nào

### 2.3 Tính toán cụ thể

```
100 triệu rows, mỗi row 100 bytes, cột salary = 8 bytes

PostgreSQL: đọc 100M x 100B = ~10 GB từ disk
ClickHouse: đọc 100M x 8B   = ~800 MB từ disk (trước khi nén)
                               ~80 MB (sau nén 10x)

-> ClickHouse đọc ít hơn ~125 lần
```

---

## 3. Data Compression

### 3.1 PostgreSQL — Nén kém

Mỗi row chứa nhiều kiểu dữ liệu xen kẽ:

```
[int, varchar, int, varchar, bigint, int, varchar, ...]
```

Kiểu dữ liệu khác nhau liên tục -> thuật toán nén không tìm được pattern hiệu quả.

### 3.2 ClickHouse — Nén cực tốt

Cùng kiểu dữ liệu nằm liền nhau:

```
age.bin: [25, 30, 22, 28, 35, 27, 31, 26, ...]
         -> toàn số nguyên, range nhỏ (18-65)
         -> nén bằng Delta encoding + LZ4
```

### 3.3 Các kỹ thuật nén ClickHouse sử dụng

**Delta encoding** (tốt cho time-series, ID tăng dần):

```
Gốc:  [1000, 1001, 1002, 1003, 1005]
Delta: [1000, 1, 1, 1, 2]  -> nén cực nhỏ vì toàn giá trị nhỏ lặp lại
```

**Dictionary encoding** (tốt cho cột low cardinality):

```
Gốc:  ["HN", "SG", "HN", "DN", "HN", "SG"]
Dict:  {0="HN", 1="SG", 2="DN"}
Data:  [0, 1, 0, 2, 0, 1]  -> từ string thành int nhỏ
```

**LZ4/ZSTD compression** áp dụng trên kết quả của các bước trên.

Kết quả thực tế: **nén 10x đến 40x** so với dữ liệu gốc. Ít data hơn = ít disk I/O hơn = nhanh hơn.

---

## 4. Vectorized Execution vs Volcano Model

### 4.1 PostgreSQL — Volcano model (row-at-a-time)

Mỗi operator xử lý 1 row rồi truyền lên operator tiếp theo:

```
         Filter (age > 25)
            ^ row 1
         Scan
            ^ row 1
         Disk
```

Vòng lặp bên trong:

```
for each row in table:
    value = get_column(row, "age")       <- function call overhead
    if value > 25:                       <- branch prediction miss
        result = get_column(row, "salary")  <- function call overhead
        sum += result
```

Vấn đề:

- Mỗi row = 1 vòng lặp = nhiều **function call overhead**
- CPU **branch prediction miss** liên tục
- **CPU cache miss** vì nhảy qua lại giữa các vùng nhớ

### 4.2 ClickHouse — Vectorized execution (batch-at-a-time)

Xử lý 1 block (65,536 giá trị) cùng lúc:

```
age_column = [25, 30, 22, 28, 35, 27, ...]  // 65536 values

// Buoc 1: Filter ca block cung luc
mask = SIMD_compare_gt(age_column, 25)
// mask = [0, 1, 0, 1, 1, 1, ...]  <- 1 instruction xu ly 8-16 gia tri

// Buoc 2: Apply mask len salary column
filtered_salary = apply_mask(salary_column, mask)

// Buoc 3: Sum ca block
sum = SIMD_sum(filtered_salary)
```

### 4.3 SIMD (Single Instruction Multiple Data)

1 lệnh CPU xử lý nhiều giá trị cùng lúc:

```
Không SIMD (PostgreSQL):
  add a[0], b[0] -> c[0]    <- 1 instruction, 1 ket qua
  add a[1], b[1] -> c[1]
  add a[2], b[2] -> c[2]
  add a[3], b[3] -> c[3]
  -> 4 instructions cho 4 ket qua

SIMD AVX-256 (ClickHouse):
  vadd [a[0..3]], [b[0..3]] -> [c[0..3]]
  -> 1 instruction cho 4 ket qua (AVX-512 xu ly 8-16 cung luc)
```

---

## 5. CPU Cache Efficiency

### 5.1 PostgreSQL — Cache utilization thấp

```
RAM layout: [id|name|age|city|salary] [id|name|age|city|salary] ...
                   ^
CPU cache line (64 bytes) chứa data của 1 row
-> Cache chỉ dùng được 8/100 bytes (cột salary)
-> Cache utilization: ~8%
```

### 5.2 ClickHouse — Cache utilization cao

```
RAM layout: [salary1|salary2|salary3|salary4|salary5|salary6|salary7|salary8]

CPU cache line (64 bytes) chứa 8 giá trị salary liền nhau
-> Cache utilization: 100%
```

Đây gọi là **cache locality** — dữ liệu cần xử lý nằm sát nhau trong memory, CPU không phải chờ RAM fetch data.

---

## 6. B-Tree Index vs Sparse Index

### 6.1 B-Tree Index (PostgreSQL)

#### Cấu trúc

B-Tree = Balanced Tree, cây cân bằng mà mọi lá cùng độ sâu.

```
                         ┌─────────────┐
              Level 0:   │   [500000]  │              <- Root
                         └──┬──────┬───┘
                            │      │
                ┌───────────┘      └───────────┐
                v                               v
         ┌─────────────┐                 ┌─────────────┐
Level 1: │[250K, 500K] │                 │[750K, 1M]   │  <- Internal
         └─┬────┬────┬─┘                 └─┬────┬────┬─┘
           │    │    │                      │    │    │
           v    v    v                      v    v    v
         ┌────┐┌────┐┌────┐             ┌────┐┌────┐┌────┐
Level 2: │Leaf││Leaf││Leaf│    ...      │Leaf││Leaf││Leaf│  <- Leaf nodes
         └────┘└────┘└────┘             └────┘└────┘└────┘
```

#### Bên trong Leaf Node

Mỗi leaf node là 1 page (8KB), chứa danh sách các (key, pointer):

```
Leaf Node (8KB page):
┌───────────────────────────────────────────────────────────┐
│ (id=1,    ctid=(0,1))   <- ctid = vi tri row tren disk    │
│ (id=2,    ctid=(0,2))      (page 0, slot 1)               │
│ (id=3,    ctid=(0,3))                                      │
│ (id=4,    ctid=(1,1))   <- row nam o page 1, slot 1       │
│ ...                                                        │
│ (id=367,  ctid=(45,3))                                     │
│ -> next_leaf ──────────> [Leaf node tiep theo]             │
└───────────────────────────────────────────────────────────┘
```

Mỗi leaf entry ~20 bytes (8 bytes key + 6 bytes ctid + overhead). 1 page 8KB chứa ~367 entries.

#### Point lookup: `SELECT * FROM employees WHERE id = 742931`

```
Buoc 1: Root node (da cache trong RAM)
        742931 > 500000 -> di phai

Buoc 2: Internal node
        742931 nam trong [500K, 750K] -> di giua

Buoc 3: Internal node (neu cay sau hon)
        ...tiep tuc so sanh

Buoc 4: Leaf node
        Tim thay (id=742931, ctid=(8234, 5))

Buoc 5: Heap fetch — doc page 8234 tu bang chinh, lay row o slot 5

-> Tong: 3-4 lan doc page (index) + 1 lan doc page (heap)
-> Rat nhanh cho point lookup!
```

#### Range scan: `SELECT * FROM employees WHERE id BETWEEN 100000 AND 200000`

```
Buoc 1-3: Tim leaf node chua id=100000 (giong point lookup)

Buoc 4: Duyet leaf nodes theo linked list:

  Leaf[100000-100367] -> Leaf[100368-100735] -> ... -> Leaf[...-200000]
       |                    |                            |
  Fetch 367 rows        Fetch 367 rows              Fetch rows
  tu HEAP               tu HEAP                     tu HEAP

100,000 rows / 367 per leaf = ~273 leaf pages can doc
+ 100,000 heap fetches (random I/O!)
```

#### Vấn đề của B-Tree

**1. Index size rất lớn — vì index MỌI row:**

```
1 ty rows x ~20 bytes/entry = ~20 GB chi cho index
+ Internal nodes overhead
-> Index co the KHONG fit trong RAM
-> Doc index cung phai di disk -> cham
```

**2. Random I/O khi fetch heap:**

```
Index scan tim duoc: ctid = [(0,1), (45,3), (8234,5), (102,7), ...]
                              ^       ^        ^         ^
                         Scattered tren disk — moi fetch la random I/O
```

**3. Write amplification:**

```
INSERT 1 row vao bang co 5 indexes:
  1. Ghi row vao heap            <- 1 write
  2. Cap nhat index_1 (B-tree)   <- co the gay page split
  3. Cap nhat index_2 (B-tree)
  4. Cap nhat index_3 (B-tree)
  5. Cap nhat index_4 (B-tree)
  6. Cap nhat index_5 (B-tree)
-> 1 INSERT = 6+ writes
```

**4. Page split — khi leaf node đầy:**

```
Truoc INSERT id=150:
  Leaf: [100, 120, 130, 140, 160, 170, 180, 190]  <- day

Sau INSERT id=150 -> SPLIT:
  Leaf A: [100, 120, 130, 140, 150]
  Leaf B: [160, 170, 180, 190]
  Parent phai cap nhat pointer -> co the cascade len tren
```

### 6.2 Sparse Index (ClickHouse)

#### Cách dữ liệu được tổ chức

ClickHouse sắp xếp dữ liệu **vật lý trên disk theo primary key** và chia thành **granules** (mặc định 8192 rows/granule):

```
PRIMARY KEY: (date, user_id)

Granule 0 (rows 0-8191):
┌──────────────────────────────────┐
│ 2024-01-01, user_1,  ...        │
│ 2024-01-01, user_2,  ...        │
│ 2024-01-01, user_3,  ...        │
│ ...                              │
│ 2024-01-01, user_8192, ...      │
└──────────────────────────────────┘

Granule 1 (rows 8192-16383):
┌──────────────────────────────────┐
│ 2024-01-01, user_8193, ...      │
│ ...                              │
│ 2024-01-02, user_150,  ...      │
└──────────────────────────────────┘

Granule 2 (rows 16384-24575):
┌──────────────────────────────────┐
│ 2024-01-02, user_151,  ...      │
│ ...                              │
│ 2024-01-03, user_500,  ...      │
└──────────────────────────────────┘
```

#### Sparse Index chỉ lưu giá trị ĐẦU TIÊN của mỗi granule

```
primary.idx file:

Mark 0 -> (2024-01-01, user_1)        <- gia tri dau cua granule 0
Mark 1 -> (2024-01-01, user_8193)     <- gia tri dau cua granule 1
Mark 2 -> (2024-01-02, user_151)      <- gia tri dau cua granule 2
Mark 3 -> (2024-01-03, user_500)      <- gia tri dau cua granule 3
Mark 4 -> (2024-01-05, user_12)       <- gia tri dau cua granule 4
...
```

So sánh kích thước index:

```
1 ty rows / 8192 = ~122,000 marks
122,000 x ~16 bytes = ~2 MB cho toan bo index

So sanh: B-Tree cho 1 ty rows = ~20 GB
         Sparse index          = ~2 MB

-> Sparse index LUON fit trong RAM
```

#### Mark file — mapping granule sang vị trí trên disk

Ngoài `primary.idx`, mỗi cột có 1 `.mrk` file:

```
salary.mrk:
Mark 0 -> offset 0 trong salary.bin
Mark 1 -> offset 65536 trong salary.bin
Mark 2 -> offset 131072 trong salary.bin
...
```

Đây là bảng tra — biết granule nào thì biết đọc từ byte nào trong file cột.

#### Tìm kiếm: `SELECT * FROM events WHERE date = '2024-01-02'`

```
Buoc 1: Binary search tren primary.idx (trong RAM, ~2MB)

  Mark 0: 2024-01-01 <- nho hon
  Mark 1: 2024-01-01 <- nho hon
  Mark 2: 2024-01-02 <- MATCH — bat dau tu day
  Mark 3: 2024-01-03 <- lon hon — dung

-> Can doc granule 2 va granule 3 (co the chua data cua 2024-01-02)

Buoc 2: Dung .mrk file -> biet offset tren disk

Buoc 3: Doc dung 2 granules (2 x 8192 = 16,384 rows)
         Bo qua TOAN BO phan con lai cua bang

Tren bang 1 ty rows -> chi doc 16K rows = skip 99.998% data
```

#### Khi nào Sparse Index KHÔNG hiệu quả?

```
PRIMARY KEY: (date, user_id)

Query: SELECT * FROM events WHERE user_id = 12345
       (khong filter theo date — cot dau tien cua key)

-> Sparse index KHONG giup duoc
-> Phai scan TOAN BO bang (full scan)
```

ClickHouse chỉ có 1 thứ tự sắp xếp vật lý (primary key order). PostgreSQL có thể tạo nhiều B-Tree index độc lập cho nhiều cột. Giải pháp của ClickHouse: dùng "skipping indexes" (minmax, bloom filter) hoặc thiết kế primary key phù hợp với query pattern.

### 6.3 So sánh tổng hợp

| | B-Tree (PostgreSQL) | Sparse Index (ClickHouse) |
|---|---|---|
| **Triết lý** | Index mọi row, tìm chính xác | Index mỗi granule, loại trừ nhanh |
| **Index size** | Lớn (GB) | Nhỏ (MB) |
| **Point lookup** | Rất nhanh O(log n) | Chậm hơn (scan 1 granule 8192 rows) |
| **Range scan** | Random I/O -> chậm | Sequential I/O -> cực nhanh |
| **Analytical query** | Chậm | Nhanh |
| **Write overhead** | Cao (update index mỗi write) | Thấp (chỉ append) |
| **Linh hoạt** | Nhiều index cho nhiều cột | 1 primary key order duy nhất |

B-Tree tối ưu cho **tìm 1 kim trong đống rơm**. Sparse Index tối ưu cho **đọc nhanh từng đống rơm lớn**.

---

## 7. Random I/O vs Sequential I/O

### 7.1 Hình dung đơn giản

Tưởng tượng bạn có 1 cuốn sách 1000 trang.

**Sequential I/O** — đọc liên tiếp:

```
Doc trang 200, 201, 202, 203, 204, 205, ...
-> Mo sach, lat tung trang — rat nhanh
-> Tay ban chi can lat lien tuc
```

**Random I/O** — đọc ngẫu nhiên:

```
Doc trang 53, roi 871, roi 12, roi 654, roi 337, ...
-> Moi lan phai lat toi lat lui tim trang
-> Ton thoi gian "tim vi tri" moi lan
```

### 7.2 Trên HDD

HDD có đĩa quay và đầu đọc vật lý:

```
         ┌──────────────────────┐
         │    Dia tu quay        │
         │   ╭───────────╮      │
         │  /   data      \     │
         │ │  ooooooooooo  │    │
         │ │ ooooooooooooo │    │
         │  \  ooooooooo  /     │
         │   ╰───────────╯      │
         │        ^              │
         │   [dau doc]           │  <- phai DI CHUYEN VAT LY den vi tri can doc
         └──────────────────────┘
```

- **Sequential**: đầu đọc đứng yên, đĩa quay qua -> đọc liên tục
- **Random**: mỗi lần đọc, đầu đọc phải NHẢY đến vị trí mới (seek)

```
Seek time: ~5-10ms moi lan
-> Random: 10,000 reads x 10ms = 100 giay
-> Sequential: doc lien tuc ~200 MB/s, 10,000 rows = vai ms
```

### 7.3 Trên SSD

SSD không có bộ phận cơ học, nhưng vẫn có chênh lệch:

```
SSD Sequential read: ~3000 MB/s (NVMe)
SSD Random read:     ~500 MB/s (NVMe)

-> Sequential van nhanh hon ~6 lan
```

Lý do: SSD đọc theo page (4KB). Random read mỗi lần đọc 1 page rời rạc, còn sequential read kernel gộp nhiều page thành 1 request lớn (read-ahead).

### 7.4 PostgreSQL — Range scan tạo Random I/O

```sql
SELECT * FROM orders WHERE date BETWEEN '2024-01-01' AND '2024-01-31'
```

B-Tree index tìm được danh sách ctid (vị trí row trên heap):

```
ctid = (page 5, slot 2)     <- row ngay 01/01
ctid = (page 8421, slot 7)  <- row ngay 03/01
ctid = (page 12, slot 1)    <- row ngay 05/01
ctid = (page 9530, slot 3)  <- row ngay 07/01
ctid = (page 44, slot 5)    <- row ngay 08/01
ctid = (page 7213, slot 2)  <- row ngay 12/01
...
```

**Tại sao ctid nằm rải rác?** Vì PostgreSQL lưu data theo **thứ tự INSERT, không phải thứ tự date**:

```
Heap (bang chinh) tren disk:

Page 0:  [order ngay 15/03] [order ngay 02/01] [order ngay 28/07]
Page 1:  [order ngay 01/01] [order ngay 22/09] [order ngay 14/05]
Page 2:  [order ngay 30/01] [order ngay 11/11] [order ngay 03/04]
Page 3:  [order ngay 19/06] [order ngay 08/01] [order ngay 25/12]
...

-> Orders cua thang 1/2024 nam SCATTERED khap noi tren disk
-> Vi khi INSERT, row dat vao page nao co cho trong
-> Khong lien quan den gia tri date
```

Kết quả:

```
De doc 100,000 orders thang 1/2024:

  Doc page 5     <- nhay den vi tri A
  Doc page 8421  <- nhay den vi tri B (xa)
  Doc page 12    <- nhay nguoc lai (xa)
  Doc page 9530  <- nhay di (xa)
  Doc page 44    <- nhay nguoc (xa)
  ...

  100,000 lan nhay qua nhay lai = RANDOM I/O

  ┌──disk──────────────────────────────────────────────┐
  │ ...X...........X..X.......X...X.........X....X...  │
  │    ^           ^  ^       ^   ^         ^    ^     │
  │    Cac row thang 1 nam rai rac                     │
  └────────────────────────────────────────────────────┘
```

### 7.5 ClickHouse — Range scan tạo Sequential I/O

ClickHouse sắp xếp data **vật lý trên disk** theo primary key:

```
PRIMARY KEY: (date, user_id)

Granule 0:   2024-01-01, 2024-01-01, 2024-01-01, ...  (8192 rows)
Granule 1:   2024-01-01, 2024-01-01, 2024-01-02, ...  (8192 rows)
...
Granule 25:  2024-01-15, 2024-01-15, 2024-01-16, ...  (8192 rows)
...
Granule 50:  2024-01-31, 2024-01-31, 2024-01-31, ...  (8192 rows)
Granule 51:  2024-02-01, ...  <- DUNG — khong can doc nua
```

Trên disk:

```
  ┌──disk──────────────────────────────────────────────┐
  │ XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.........  │
  │ ^ thang 1 nam LIEN NHAU ^              ^ thang 2   │
  └────────────────────────────────────────────────────┘

  Doc tu granule 0 -> granule 50: MOT DUONG THANG
  Khong nhay, khong quay lai
  = Sequential I/O
```

### 7.6 Tốc độ thực tế

```
Doc 100,000 rows thang 1/2024:

PostgreSQL (Random I/O):
  100,000 rows x 1 page moi row = 100,000 page reads
  Moi page 8KB, nhung random -> moi read ~0.1ms (SSD)
  100,000 x 0.1ms = ~10 giay
  (HDD: 100,000 x 5ms = ~500 giay!)

ClickHouse (Sequential I/O):
  ~50 granules x 8192 rows = ~400K rows lien tiep
  Doc sequential tren SSD: ~3 GB/s
  50 granules x ~64KB moi granule (da nen) = ~3.2 MB
  3.2 MB / 3 GB/s = ~0.001 giay (1 ms)
```

```
PostgreSQL:  ~10,000 ms
ClickHouse:  ~1 ms

-> Chenh lech: ~10,000 lan
```

### 7.7 Tại sao PostgreSQL không sắp xếp data trên disk?

Vì nó cần phục vụ OLTP — INSERT/UPDATE nhanh:

```
Neu data phai luon sorted theo date:

  INSERT 1 row ngay 2024-01-15
  -> Phai CHEN vao GIUA bang
  -> Dich chuyen hang trieu rows phia sau
  -> INSERT tu O(1) thanh O(n) — CUC CHAM
```

PostgreSQL chọn: INSERT append vào cuối hoặc page có chỗ trống -> O(1). Đánh đổi: range scan phải random I/O.

ClickHouse chấp nhận trade-off ngược lại: INSERT ghi vào "part" mới (sorted trong part đó), background merge gộp parts nhỏ thành parts lớn. INSERT nhanh (append-only, batch), read cực nhanh (data sorted, sequential I/O), nhưng không thể update/delete 1 row hiệu quả.

---

## 8. Parallel Processing

### 8.1 PostgreSQL

```
Query: SELECT AVG(salary) FROM employees

1 query -> 1 process -> 1 CPU core (mac dinh)
(parallel query co tu PG 9.6 nhung han che)
```

### 8.2 ClickHouse

```
Query: SELECT AVG(salary) FROM employees

Tu dong chia du lieu thanh N parts:

Core 0:  AVG(salary) tu part 0-3
Core 1:  AVG(salary) tu part 4-7
Core 2:  AVG(salary) tu part 8-11
...
Core 15: AVG(salary) tu part 60-63

-> Merge ket qua cuoi cung
```

Trên server 16 cores -> nhanh hơn gần **16 lần** cho 1 query.

---

## 9. MVCC Overhead

### 9.1 PostgreSQL — MVCC (Multi-Version Concurrency Control)

Mỗi row có thêm metadata ẩn:

```
[xmin=100, xmax=105, id=1, name="A", salary=15M]   <- phien ban cu
[xmin=105, xmax=inf, id=1, name="A", salary=18M]   <- phien ban moi sau UPDATE
```

- Mỗi SELECT phải kiểm tra: "row này có visible với transaction hiện tại không?"
- Dead tuples tích tụ -> cần VACUUM để dọn dẹp
- Table bloat -> scan chậm hơn theo thời gian

### 9.2 ClickHouse — Không có MVCC

- Không hỗ trợ UPDATE/DELETE row đơn lẻ (theo cách truyền thống)
- Không có dead tuples, không cần vacuum
- Data luôn compact, luôn nhanh

---

## 10. Tổng hợp benchmark

```
Query: SELECT AVG(salary) FROM employees  -- 100 trieu rows

PostgreSQL:
  Disk I/O:    doc ~10 GB (toan bo row)
  Compression: khong dang ke
  Execution:   row-by-row, 1 core
  Cache:       ~8% utilization
  Overhead:    MVCC visibility check moi row
  = 30-120 giay

ClickHouse:
  Disk I/O:    doc ~80 MB (chi cot salary, da nen)
  Compression: 10x nen
  Execution:   vectorized SIMD, 16 cores song song
  Cache:       100% utilization
  Overhead:    khong co
  = 0.05-0.2 giay
```

Mỗi yếu tố nhân lên:

| Yếu tố | Hệ số tăng tốc |
|---|---|
| Column storage | ~10x |
| Compression | ~10x |
| Vectorized + SIMD | ~5-10x |
| Parallel processing | ~16x (tùy cores) |
| Cache efficiency | ~2-3x |

Tổng cộng: **100x - 1000x** nhanh hơn cho analytical queries.

---

## 11. Khi nào dùng gì?

### PostgreSQL

- App thông thường, CRUD operations
- Transaction processing (chuyển tiền, đặt hàng)
- Dữ liệu dưới vài chục triệu rows
- Cần UPDATE/DELETE row đơn lẻ
- Cần ACID transactions
- Cần nhiều index cho nhiều kiểu query khác nhau

### ClickHouse

- Analytics, báo cáo, dashboard
- Log aggregation, metrics, monitoring
- Time-series data
- Event tracking, clickstream
- Aggregate hàng tỷ rows
- Workload chủ yếu là INSERT batch + SELECT aggregate

### Kiến trúc kết hợp

Trong thực tế, một hệ thống production hoàn chỉnh thường **dùng cả hai**:

```
Users/App -> PostgreSQL (OLTP) -> ETL/CDC -> ClickHouse (OLAP) -> BI/Dashboard
```

- PostgreSQL thu thập và quản lý dữ liệu giao dịch
- ETL pipeline đồng bộ dữ liệu sang ClickHouse
- ClickHouse phục vụ phân tích và báo cáo

Hai hệ thống bổ sung cho nhau, không thay thế nhau.

### Database phổ biến theo từng loại

| OLTP | OLAP |
|---|---|
| PostgreSQL | ClickHouse |
| MySQL | Apache Druid |
| Oracle | Google BigQuery |
| SQL Server | Amazon Redshift |
| MongoDB | Snowflake |
| CockroachDB | Apache Doris |
