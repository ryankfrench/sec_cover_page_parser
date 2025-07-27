import new_text_parser.txt_layout_parser as txt_layout_parser
import nlp_text_search.nlp_text_search as nlp_text_search

def test_nlp_text_search(text: str):
    searcher = nlp_text_search.NLPTextSearch()
    result = searcher.find_best_match("IRS Employer Number", text)
    print(result)
    print(f"{text[result[1]:result[2]]}")


if __name__ == "__main__":
    path = '/home/rfrench/projects/sec_cover_page_parser/test_filings/1018724/0000891020-98-001352/0000891020-98-001352.txt'
    with open(path, 'r') as f:
        text = f.read()

    # test_nlp_text_search(text)
    txt_layout_parser.main(text)
