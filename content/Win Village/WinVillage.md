Here is the given HTML content converted to Markdown:

# Homepage

![image1](images/image1.png)

- Net reservations
    - via form
    - Need system for employees to be informed of new reservations, CRUD
      for reservations, etc.
    - flow
- Calendar -> Preview -> Reserve
    - via phone
    - backend CRUD system for Win Village employees to input data
    - knowledge base system for answering questions

# Customer management system

- CRUD operations
- mailing list
- ticket system for managing problems?
- Search customer
- Customer details
- has_paid
- payment_successful
- Customer Card (?)

# Inventory management

- Grocery inventory
- Room inventory?

# Sales/Payment management

# Purchase Order management

# Room/Reservation management

- Price Change during set times or days (holidays, etc.)
- Reserved rooms (reserved via site or phone)
- Non-reserve rooms x 8 (reserved at the counter, hourly/short stay)

# BBQ sets

- Purchase along with reserve
- Can take home (not rental)

# Grocery

- Purchase food to BBQ

CSV\

# 管理パネルのナビゲーション

## ダッシュボード　ー　大事な情報をまとめて見るページ

## 顧客管理

- 顧客カード ー 顧客の問題を記録するページ
- 全部のチケットを見る ー 全部の問題チケットを見るページ

## 売上管理

+ 売上帳を見る
+ 全部の予約を見る
+ 予約を制作する

## 仕入管理

- 仕入帳を見る
- 仕入れを制作する

## 在庫管理

- 在庫を見る
- 在庫のアイテムを制作する
- 在庫のカテゴリーを見る
- 在庫のカテゴリーを制作する

# 2024-3-6 meeting

# Timetable

Middle space rental for 500yen per hour.

They also need time-based reservations. But later.

Sauna reservation time will be decided after reservation.

# 宿泊

４つの部屋

# 連泊セット

１泊１万円
２泊、一日目１万、二日目は８千円とか

# 貸し切り ー マックスでレンタル （グループ用）

全部の部屋を貸したりするシステム

# お風呂だけレンタル

# special day system

Need to focus on making this quick and easy to use.

# BBQ set

無料BBQセットがある。炭を買ってくるか、WINVILLAGEで買うか。

# 延長

Late fees.

# 人数制

ひろばをBBQの場所として貸したら、人数を決めないといけない。

# Products

- Rooms
- Space
- Bath
- BBQ
- Food

# jalanのようなサイトを作らないと

# Priority

- Overnight stays
- BBQ space rental (ex. 20 people max)
- Food option

# Children

2A stay = 35,000 yen
2A+1elementary = 40,000 yen

# confirmation email

- Website link
- Cancellation ability
- Price breakdown + final price
- reservation period
- checkin/checkout time
- Access information

# 2024-3-7 Synthesis

Here are the main takeaways.

- The pricing system is going to be complicated, but also seems to be
  what they want most.
- Winvillage is worried about their staff being able to use the admin
  dashboard.
- The priority features (overnight stay reservations, BBQ space rentals,
  and food options) are features that I've mostly been working on already.
- Winvillage has a significant number of different policies and
  business decisions they need to decide:
    - Pricing for late fees
    - Max occupants for outdoor space rentals
    - BBQ sets
    - Reservation options

## Pricing System

The pricing system has several components.

- There are two kinds of reservations: Overnight and Short-Term
- My current understanding is that:
    - Reservations of type Overnight are only for rooms.
    - Several different products are reserved on a Short-Term basis:
        - Rooms
        - Outdoor space
        - Sauna
        - Grills
        - Other items (tents, chairs, etc.)
    - Winvillage wants the ability to rent out rooms and outdoor space
      at different prices arbitrarily.
    - The result is that short-term reservations are going to be necessary.



