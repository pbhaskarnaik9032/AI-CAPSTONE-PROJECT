# AI-CAPSTONE-PROJECT

## Module 1 - Data Pipeline

### Project Overview

This project builds an end-to-end data pipeline using book data from Books to Scrape.

The pipeline follows:

Website → Scraping → Cleaning → CSV → SQLite → SQL → Pandas

### Data Source

https://books.toscrape.com/

### Categories Collected

The project collects books from 5 categories:

- Travel
- Mystery
- Science Fiction
- Classics
- Historical Fiction

### Data Collected

For each book, the following information is collected:

- Title
- Price
- Star Rating
- Availability
- Category

### Data Cleaning

The raw data is cleaned by:

- Converting GBP price to numeric format
- Converting GBP price to INR
- Converting star ratings to numbers
- Converting availability to True/False
- Checking missing values
- Checking duplicate rows

### Dataset

- Total books: 86
- Total categories: 5
- Missing values: 0
- Duplicate rows: 0

### Output Files

The project creates:

- `books_cleaned.csv`
- `books_database.db`

### SQLite Database

The database contains two related tables.

#### categories

- `category_id`
- `category_name`

#### books

- `book_id`
- `title`
- `price_gbp`
- `price_inr`
- `star_rating`
- `in_stock`
- `category_id`

The `category_id` in the books table is a foreign key connected to the categories table.

### SQL Queries

The project demonstrates:

1. SELECT
2. WHERE
3. ORDER BY
4. LIMIT
5. DISTINCT
6. BETWEEN
7. JOIN

SQL results are read into Pandas using:

`pandas.read_sql_query()`

The SQL JOIN is also reproduced using:

`pandas.merge()`

### Technologies Used

- Python
- Requests
- BeautifulSoup
- Pandas
- SQLite

### Module 1 Checklist

- [x] 60+ books collected
- [x] 3+ categories represented
- [x] Clean, correctly typed data
- [x] GBP price column
- [x] INR price column
- [x] SQLite database built
- [x] Two related tables
- [x] Primary key
- [x] Foreign key
- [x] 5+ SQL queries
- [x] SQL JOIN
- [x] Results read using pandas.read_sql_query()
- [x] JOIN reproduced using pandas.merge()
- [x] README documentation
