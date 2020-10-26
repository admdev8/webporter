# What's Webporter
WebPorter is a sample web crawler for dowloading page or website
you can use it to backup website or download pages

# How to use
you can find the usage
usage: webporter.py [-h] [-c COOKIE] [-u URL] [-s URLS] [-d DEPTH] [-t THREADS] [-e] [--log_path LOG_PATH] [-l LOG_LEVEL]

optional arguments:
  -h, --help            show this help message and exit
  -c COOKIE, --cookie COOKIE
                        cookie from the website
  -u URL, --url URL     The address where you want to get the source code
  -s URLS, --urls URLS  Download multiple urls from file
  -d DEPTH, --depth DEPTH
                        Number of loops to get links
  -t THREADS, --threads THREADS
                        Number of threads for task execution
  -e, --entire          Download entire website
  --log_path LOG_PATH   Log path
  -l LOG_LEVEL, --log_level LOG_LEVEL
                        Log level

# Example
## case 1
download a single page
python webporter.py -u http://techyself.com

## case 2
download the whole page and reference page
python webporter.py -u http://techyself.com -e

## case 3
download pages from a list
python webporter.py -s url_list.txt

# How to contribute
Welcome to upstream features or issue question
