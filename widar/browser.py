from playwright.sync_api import sync_playwright


def get_url(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate to the URL
        page.goto(url)

        # Wait for some time for JavaScript to execute (adjust as needed)
        page.wait_for_timeout(10000)

        # Get the page content
        res = page.content()

        # Close the browser
        browser.close()

    return res