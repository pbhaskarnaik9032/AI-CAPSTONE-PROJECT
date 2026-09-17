# Module 1 - Data Pipeline

This module builds an end-to-end data pipeline using book data from Books to Scrape.

## Project Workflow

Website → Scraping → Cleaning → CSV → SQLite → SQL → Pandas

## Data Source

Books to Scrape:

https://books.toscrape.com/

## Data Collection

The notebook uses `requests` and `BeautifulSoup` to collect books from 5 categories:

- Travel
- Mystery
- Science Fiction
- Classics
- Historical Fiction

A total of 86 books were collected, satisfying the minimum 60-book requirement.

## Data Fields

The raw dataset contains:

- title
- price
- rating
- availability
- category

## Data Cleaning

The pipeline:

- converts price into numeric GBP values
- creates INR prices using the project conversion rate
- converts star ratings to numeric values
- converts availability to a boolean `in_stock` field
- checks missing values and duplicates

The cleaned dataset contains 86 rows and 5 main fields used for the final CSV/database pipeline.

## CSV Output

The cleaned data is saved as:

`books_cleaned.csv`

Cleaned fields include:

- title
- price_gbp
- price_inr
- star_rating
- in_stock
- category

## SQLite Database

The pipeline creates:

`books_database.db`

The database uses relational tables for books and categories.

The `books` table uses `book_id` as the primary key, and `category_id` is used as a foreign key linking each book to the `categories` table.

The notebook verifies:

- 86 books inserted
- primary key present
- foreign key present
- 5 categories stored

## SQL Queries Completed

The notebook executes 7 SQL queries demonstrating:

1. SELECT
2. WHERE
3. ORDER BY
4. LIMIT
5. DISTINCT
6. BETWEEN
7. JOIN

## Pandas Merge

The SQL results are also combined with category information using a Pandas merge on `category_id`.

## Outputs

- `Module_1_Data_Pipeline_ipynb.ipynb` - complete implementation and outputs
- `books_cleaned.csv` - cleaned book dataset
- `books_database.db` - SQLite database
