import requests
from io import StringIO
import pandas as pd
import numpy as np
import re
from pandas.tseries.offsets import DateOffset
from bs4 import BeautifulSoup


def scrape_rba():
    url = "https://www.rba.gov.au/statistics/cash-rate/#cash-rate-chart"
    response = requests.get(url)

    if response.status_code == 200:
        html_content = response.content
        print("Page fetched successfully!")
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")

    soup = BeautifulSoup(html_content, 'html.parser')

    table = soup.find('table', {'id': 'datatable'})

    df = pd.read_html(StringIO(str(table)), index_col=0)[0]
    df = df.loc[:"Legend:"].iloc[:-1]

    # compute the mean rate back when there was a corridor
    rate_lo = df.iloc[:, 1].str.split(" to ").str.get(0)
    rate_hi = df.iloc[:, 1].str.split(" to ").str.get(1).fillna(rate_lo)
    rate = (rate_hi.astype(float) + rate_lo.astype(float)) / 2

    rate.index = pd.to_datetime(rate.index).rename("date")
    rate.name = "rate"

    rate = rate.sort_index()

    return rate


def scrape_boc():
    """"""
    e_dt = pd.Timestamp("now")
    s_dt = e_dt - DateOffset(years=24)
    s_dt = pd.to_datetime("2018-05-01")
    url = "https://www.bankofcanada.ca/stats/results//csv?" \
          "rangeType=dates&ByDate_frequency=daily&" \
          f"lP=lookup_canadian_interest.php&sR={s_dt.strftime('%Y-%m-%d')}&" \
          f"se=L_V39079&dF={s_dt.strftime('%Y-%m-%d')}&" \
          f"dT={e_dt.strftime('%Y-%m-%d')}"
    rate = pd.read_csv(url, skiprows=11, index_col=0, parse_dates=True) \
               .iloc[:, 0]
    rate = rate.replace(" Bank holiday", np.nan).astype(float)
    rate = rate.rename("rate").rename_axis(index="date")
    rate = rate.sort_index()
    dr = rate.loc[rate.diff().abs() > 0]

    # dates
    url = "https://www.bankofcanada.ca/2022/07/2023-schedule-interest-rate-announcements/"
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')

    ul = soup.find("main", {"id": 'main-content'}) \
        .find_all("ul")[0]

    dates = []
    for li in ul.find_all('li'):
        text = re.sub("\*", "", li.get_text())
        dates.append(pd.to_datetime(text + " 2023"))

    for _dt in dates:
        print(_dt)

    dt = pd.Series(dates, name="date_meeting").to_frame()
    pd.merge_asof(dt, dr, left_on="date_meeting", right_index=True)

    return rate


def scrape_norges():
    """"""
    root = "https://www.norges-bank.no/en/topics/Monetary-policy/Monetary-policy-meetings"

    pat_meeting = re.compile(
        r'meeting[ a-z]*on (\d{1,2} [A-Za-z]+,? \d{4})'
    )

    res = []

    for _dt in pd.period_range("2010-01", "2023-12", freq="M"):
        y, m = _dt.year, _dt.strftime("%B")

        response = requests.get(
            f"{root}/{y}-Key-policy-rate-decisions/Rate-decision-{m}-{y}/"
        )

        if response.status_code != 200:
            response = requests.get(
                f"{root}/{y}/rate-decision-{m}-{y}/"
            )

            if response.status_code != 200:
                response = requests.get(f"{root}/{y}/{m}-{y}/")

                if response.status_code != 200:
                    continue

        html_content = response.content
        soup = BeautifulSoup(html_content, 'html.parser')

        # search for text about meeting date
        date_meeting = list(set(pat_meeting.findall(str(soup).lower())))

        # search for text about publication date
        span_pub = soup.find("span", {"class": "prop"})

        # extract the date part
        pub_date = span_pub.find_next_sibling(string=True).strip()

        # extract the time part
        span_pub_time = soup.find("span", {"class": "time"})
        pub_time = span_pub_time.string

        datetime_pub = pd.to_datetime(
            " ".join((pub_date, pub_time))).tz_localize("Europe/Oslo")

        res.append([date_meeting, datetime_pub])

    pd.DataFrame.from_records(res, columns=["meeting", "publication"]) \
        .to_csv("temp/norges.csv")


def scrape_riks():
    """"""
    _y = 2023
    url = "https://www.riksbank.se/en-gb/press-and-published/" \
          "minutes-of-the-executive-boards-monetary-policy-meetings/" \
          f"?year={_y}"
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')

    div = soup.find('div', class_='listing-block__body')
    ul = div.find('ul')

    date_pattern = re.compile(r'\d{1,2} [A-Za-z]+ \d{4}')

    dates = []
    for li in ul.find_all('li'):
        text = li.get_text()
        match = date_pattern.search(text)
        if match:
            dates.append(pd.to_datetime(match.group()) + DateOffset(days=1))

    for _d in sorted(dates):
        print(_d.date())


def scrape_boe():
    """"""
    url = "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"

    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')

    tbl = soup.find('section', {"class": "page-section  "}) \
        .find("table")
    df = pd.read_html(StringIO(str(tbl)))[0]
    df.iloc[:, 0] += " 2022"
    print(pd.to_datetime(df.iloc[:, 0]))


def scrape_fomc():
    """"""
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')

    dt = pd.DatetimeIndex([])

    for _y in (2021, 2022, 2023):
        h4 = soup.find('h4', string=f'{_y} FOMC Meetings')

        ms = h4.parent.parent.find_all("div", {
            "class": ['fomc-meeting__month col-xs-5 col-sm-3 col-md-2',
                      'fomc-meeting--shaded fomc-meeting__month col-xs-5 col-sm-3 col-md-2']})
        ms = [_m.text.split("/")[-1] for _m in ms]
        ds = h4.parent.parent.find_all("div", {
            "class": 'fomc-meeting__date col-xs-4 col-sm-9 col-md-10 col-lg-1'})
        ds = [re.sub("\*", "", _d.text.split("-")[-1]) for _d in ds]

        dt = dt.union(
            pd.to_datetime([f"{_m} {_d}, {_y}" for _m, _d in zip(ms, ds)],
                           format='mixed', dayfirst=False)
        )
