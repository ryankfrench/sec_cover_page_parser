# sec_cover_page_parser
This goal of this project is to accurately parse company information from the cover page of sec filings. Of specific interest is the company address since it often does not match the address listed in the header.

I think the parser logic will be like this:

1. check for xbrl data: If exists parse the data from the xbrl markup.
2. check for html data: If exists parse the data from the html markup.
