# CNNWebScraper

A simple Python Beautifulsoup script to gather article contents from CNN and put them into a CSV file. Created to develop a ML-based bias  analyzer on popular news websites for [AGORAx](https://theagorax.com/) (plans delayed indefinitely).

Author: [Faris Durrani](https://github.com/farisdurrani) <br>
Source: [GitHub](https://github.com/farisdurrani/CNNWebScraper) <br>
Implemented: October 2021

## How to Use

### Requirements
1. Use Python 3.6.8
2. Install the required packages in `requirements.txt`

### Usage
1. Choose which year and topics to scrape from https://www.cnn.com/, modifying appropriately `selected_years` in line 206 and `topics` in line 209.
2. Run the script and see the output in a new file labeled `cnn_articles.csv`, in addition with an `errors.txt` file that lists all errors encountered like broken links. The reader may see some sample outputs in the `output_samples` directory.

> **Note** <br>
> This script only parses text strings, not media items like pictures and videos.

## Output

