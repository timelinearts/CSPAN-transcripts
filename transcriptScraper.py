# Copyright 2021 Christian Brickhouse
#
# This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import argparse
import logging
import csv
from dataclasses import dataclass
from datetime import timedelta
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)


@dataclass
class TranscriptEntry:
    speaker: str
    text: str
    start_time: int


def getTranscriptChunk(tds, browser):
    transcriptChunk = []
    for td in tds:
        if td.get_attribute("class") == "image":
            continue
        a = None
        try:
            a = td.find_element(By.CLASS_NAME, "hidden-full-transcript-link")
            browser.execute_script("arguments[0].click();", a)
            logger.debug("wait for element to appear")
            e = WebDriverWait(browser, 1).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "hidden-full-transcript-text")
                )
            )
            logger.debug("element appeared within expected time")
        except NoSuchElementException as ex:
            logger.debug(".hidden-full-transcript-link element not found")
            pass
        # Following isn't quite correct; some transcript text is
        #  in elements without the stated class
        if a:
            # Has full transcript dropdown widget
            logger.debug("found full transcript dropdown")
        else:
            logger.debug("short transcript only")
        # Grab the short transcript <p> element and the text shall set you free
        short_transcript = td.find_element(By.CLASS_NAME, "short_transcript")
        speaker = short_transcript.find_element(By.XPATH, "./preceding-sibling::strong")
        # print(speaker.text)
        logger.debug("short_transcript_text='%s'", short_transcript.text)
        transcriptChunk.append(short_transcript.text.strip())

        # chunks = td.find_elements(By.CLASS_NAME, "transcript-time-seek")
        # if len(chunks):
        #     logger.info("alt 1", chunks)
        #     print("chunks", chunks)
        #     for chunk in chunks:
        #         print("\tchunk", chunk)
        #         if chunk.text.strip() == "":
        #             continue
        #         transcriptChunk.append(chunk.text)
        # else:
        #     # alt 1
        #     logger.info("alt 2")
        #     try:
        #         fullts = td.find_element(By.CLASS_NAME, "show-hidden-full-transcript")
        #         print("fullts", fullts)
        #     except NoSuchElementException:
        #         logger.debug(".show-hidden-full-transcript not found ")
        #         pass
    return " ".join(transcriptChunk)


def getTimestamp(row):
    header = row.find_element(By.TAG_NAME, "th")
    stamp = [int(x) for x in header.text.split(":")]
    t = timedelta(hours=stamp[0], minutes=stamp[1], seconds=stamp[2])
    return t.total_seconds()


def faveOutput(chunks, times):
    rows = []
    for i in range(len(chunks)):
        row = ["?", "?", str(times[i]), str(times[i + 1]), str(chunks[i])]
        rows.append("\t".join(row))
    return "\n".join(rows)


def get_speaker(row, browser):
    speaker = row.find_element(By.TAG_NAME, "strong")
    return speaker.text


def main(url, outName):
    ffops = webdriver.FirefoxOptions()
    ffops.headless = True
    browser = webdriver.Firefox(options=ffops)

    browser.get(url)

    duration = browser.find_element(By.CLASS_NAME, "jw-video-duration").text
    dur = [int(x) for x in duration.split(":")]
    duration = timedelta(hours=dur[0], minutes=dur[1], seconds=dur[2]).total_seconds()

    sec = browser.find_element(By.CLASS_NAME, "transcript")
    rows = sec.find_elements(By.TAG_NAME, "tr")
    transcript_entries: TranscriptEntry = []
    transcript = []
    times = []
    try:
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            speaker = get_speaker(row, browser)
            chunk = getTranscriptChunk(tds, browser)
            time = getTimestamp(row)
            transcript.append(chunk)
            times.append(time)
            te = TranscriptEntry(speaker=speaker, text=chunk, start_time=time)
            transcript_entries.append(te)
    finally:
        browser.close()
    times.append(duration)

    # outText = faveOutput(transcript, times)

    with open(outName, "w") as f:
        csvwriter = csv.writer(f)
        for te in transcript_entries:
            # f.write(f"{te.start_time}, {te.speaker}, {te.text}\n")
            csvwriter.writerow([te.start_time, te.speaker, te.text])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("url", help="The cspan url to get a transcript from.")
    parser.add_argument(
        "output", help="Name of file that transcript should be written to."
    )
    args = parser.parse_args()
    main(args.url, args.output)
