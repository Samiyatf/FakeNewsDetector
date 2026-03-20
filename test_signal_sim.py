import re

tests = {
	'year_in_sentence': "One of the most thrilling videos I've seen in 2026 is the footage shot on a pair of Meta Ray-Ban glasses by a shirtless man.",
	'start_byline': "By Jane Doe\nThis is a lead sentence of an article.",
	'in_sentence_by': "The ball was thrown by the quarterback and hit the receiver.",
	'percent_and_unit': "The study found that 45% of respondents and 1,200 people reported issues.",
	'citation_present': "The report (see http://example.com/study) shows 75% improvement.",
	'quotes_unattributed': 'He said "This is a big deal" and moved on.',
	'hedging_example': "It may suggest a trend, but further study is needed.",
}


def analyze_text(sample_text):
	print('\n--- Sample (first 200 chars) ---')
	print(sample_text[:200] + ('...' if len(sample_text) > 200 else ''))

	# Author detection: only when 'by' at start of line or start of text
	author_rx = re.compile(r'(?:^|\n)\s*by\s+([A-Z][^\r\n]{2,80})', re.I | re.M)
	author_matches = author_rx.findall(sample_text)

	# URLs/citations
	url_rx = re.compile(r'https?://[^\s\)]+', re.I)
	urls = url_rx.findall(sample_text)
	unique_urls = list(dict.fromkeys(urls))

	# Hedging words
	hedge_words = ['may', 'might', 'could', 'possibly', 'suggests', 'appears', 'seem', 'likely', 'reportedly', 'according to', 'claims']
	hedge_rx = re.compile(r'\b(' + '|'.join([re.escape(w) for w in hedge_words]) + r')\b', re.I)
	hedge_matches = hedge_rx.findall(sample_text)

	# Suspicious stats (improved heuristic)
	stat_rx = re.compile(r"\b\d{4,}(?:,\d{3})*(?:\.\d+)?(?:\s?%| percent)?\b|\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s?%| percent)?\b")
	stat_matches = []
	for m in stat_rx.finditer(sample_text):
		s = m.group(0)
		idx = m.start()
		context = sample_text[max(0, idx - 80):min(len(sample_text), idx + 80)]
		# normalize
		numOnly = re.sub(r"[,\s%]", "", s)
		numOnly = re.sub(r"percent", "", numOnly, flags=re.I)
		# skip years
		if re.match(r"^\d{4}$", numOnly):
			year = int(numOnly)
			if 1900 <= year <= 2100:
				continue
		if re.search(r"\bin\s+\d{4}\b|\byear\s+\d{4}\b", context, flags=re.I):
			continue
		after = sample_text[idx + len(s): idx + len(s) + 40].lower()
		before = sample_text[max(0, idx - 20): idx].lower()
		isPercent = bool(re.search(r"%|\bpercent\b", s + ' ' + after, flags=re.I))
		unitMatch = bool(re.search(r"\b(people|deaths|cases|votes|dollars|usd|km|kilometers|miles|kg|tons|million|billion|thousand|k\b)\b", after + ' ' + before))
		hasSourceNearby = bool(re.search(r"source|according|study|survey|report|cdc|who|doi|journal|http|https|www\.|doi:", context, flags=re.I))

		# If it's a percent and there's no nearby source, mark as suspicious.
		if isPercent and not hasSourceNearby:
			stat_matches.append(s)
			continue

		# Flag numbers with units (without source nearby)
		if unitMatch and not hasSourceNearby:
			stat_matches.append(s)

	# Unattributed quotes (quoted strings)
	quote_rx = re.compile(r'"([^\"]{1,240})"')
	quote_matches = quote_rx.findall(sample_text)

	print('\n--- Detection results ---')
	print('Author matches (count):', len(author_matches))
	print('Author matches:', author_matches)
	print('Unique URLs (count):', len(unique_urls))
	print('URLs:', unique_urls)
	print('Hedging matches (count):', len(hedge_matches))
	print('Hedging matches:', hedge_matches)
	print('Suspicious stats matches (count):', len(stat_matches))
	print('Suspicious stats matches:', stat_matches)
	print('Unattributed quotes (count):', len(quote_matches))
	print('Quotes:', quote_matches)


for name, text in tests.items():
	print('\n=======================')
	print('TEST:', name)
	analyze_text(text)
