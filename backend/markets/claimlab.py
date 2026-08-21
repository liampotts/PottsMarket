import hashlib
import json
import re
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from youtube_transcript_api import YouTubeTranscriptApi


YOUTUBE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{6,20}$')
FUTURE_LANGUAGE = re.compile(
    r"\b(will|expects? to|forecast(?:s|ed)? that|going to|set to|plans? to|"
    r"by 20\d{2}|next (?:week|month|quarter|year))\b",
    re.IGNORECASE,
)
NON_MARKET_LANGUAGE = re.compile(
    r"\b(i will|i'll|i'm (?:just )?going|we will|we'll|you will|you'll|"
    r"if i|if we|if you|thanks for watching)\b",
    re.IGNORECASE,
)


class ClaimLabError(Exception):
    pass


def extract_youtube_id(url):
    parsed = urlparse((url or '').strip())
    host = parsed.netloc.lower().split(':')[0]
    video_id = ''

    if host in {'youtu.be', 'www.youtu.be'}:
        video_id = parsed.path.strip('/').split('/')[0]
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'}:
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        else:
            parts = [part for part in parsed.path.split('/') if part]
            if len(parts) >= 2 and parts[0] in {'shorts', 'embed', 'live'}:
                video_id = parts[1]

    if not YOUTUBE_ID_PATTERN.match(video_id):
        raise ClaimLabError('Enter a valid public YouTube video URL.')
    return video_id


def canonical_youtube_url(video_id):
    return f'https://www.youtube.com/watch?v={video_id}'


def _fetch_json(url, payload=None, headers=None, timeout=30):
    request_headers = {
        'Accept': 'application/json',
        'User-Agent': 'PottsMarket-ClaimLab/1.0',
        **(headers or {}),
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        request_headers['Content-Type'] = 'application/json'

    request = Request(url, data=data, headers=request_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ClaimLabError(f'Upstream request failed: {error}') from error


def fetch_youtube_document(url):
    video_id = extract_youtube_id(url)
    canonical_url = canonical_youtube_url(video_id)

    try:
        metadata = _fetch_json(
            'https://www.youtube.com/oembed?url='
            f'{quote(canonical_url, safe="")}&format=json',
            timeout=15,
        )
    except ClaimLabError:
        metadata = {}

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=['en'])
    except Exception as error:
        raise ClaimLabError(f'No accessible English transcript was found: {error}') from error

    segments = [
        {
            'text': snippet.text.strip(),
            'start': round(float(snippet.start), 2),
            'duration': round(float(snippet.duration), 2),
        }
        for snippet in fetched
        if snippet.text and snippet.text.strip()
    ]
    content = ' '.join(segment['text'] for segment in segments)
    if not content:
        raise ClaimLabError('The video transcript was empty.')

    return {
        'external_id': video_id,
        'canonical_url': canonical_url,
        'title': metadata.get('title') or f'YouTube video {video_id}',
        'author': metadata.get('author_name', ''),
        'metadata': metadata,
        'language': getattr(fetched, 'language_code', 'en'),
        'segments': segments,
        'content': content,
        'content_hash': hashlib.sha256(content.encode('utf-8')).hexdigest(),
    }


def _as_aware_datetime(value, default):
    if not value:
        return default
    parsed = parse_datetime(str(value))
    if parsed is None:
        return default
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _normalize_candidate(candidate, source_url, method):
    now = timezone.now()
    closes_at = _as_aware_datetime(candidate.get('closes_at'), now + timedelta(days=14))
    resolves_at = _as_aware_datetime(candidate.get('resolves_at'), now + timedelta(days=90))
    if resolves_at <= closes_at:
        resolves_at = closes_at + timedelta(days=30)

    statement = str(candidate.get('statement') or '').strip()[:500]
    criteria = str(candidate.get('resolution_criteria') or '').strip()
    if len(statement) < 15 or len(criteria) < 20:
        return None

    try:
        confidence = min(1, max(0, float(candidate.get('confidence', 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5

    try:
        excerpt_start = int(candidate.get('excerpt_start_seconds'))
    except (TypeError, ValueError):
        excerpt_start = None

    return {
        'statement': statement,
        'excerpt': str(candidate.get('excerpt') or '').strip()[:2000],
        'excerpt_start_seconds': excerpt_start,
        'rationale': str(candidate.get('rationale') or '').strip()[:3000],
        'resolution_criteria': criteria[:5000],
        'resolution_source_url': str(
            candidate.get('resolution_source_url') or source_url
        ).strip()[:1000],
        'closes_at': closes_at,
        'resolves_at': resolves_at,
        'confidence': confidence,
        'extraction_method': method,
    }


def _extract_with_llm(title, source_url, content):
    base_url = getattr(settings, 'CLAIM_LLM_BASE_URL', '').strip().rstrip('/')
    if not base_url:
        return []

    model = getattr(settings, 'CLAIM_LLM_MODEL', 'Qwen/Qwen3.5-2B')
    api_key = getattr(settings, 'CLAIM_LLM_API_KEY', '').strip()
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    prompt = f"""
You are the claim extraction engine for a play-money forecasting market.
Read the source transcript and return a JSON object with a `claims` array.
Create at most five binary, falsifiable, future-facing claims. Each claim must
have an objective deadline and a public resolution source. Reject opinions,
vague predictions, moral judgments, and claims that cannot resolve YES or NO.

Each item must contain:
statement, excerpt, excerpt_start_seconds, rationale, resolution_criteria,
resolution_source_url, closes_at, resolves_at, confidence.

Use ISO-8601 timestamps. Confidence is 0 to 1 and measures extraction quality,
not the probability that the event happens. Do not include markdown.

Source title: {title}
Source URL: {source_url}
Transcript:
{content[:30000]}
""".strip()
    payload = {
        'model': model,
        'temperature': 0.1,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': 'Return strict JSON only.'},
            {'role': 'user', 'content': prompt},
        ],
    }
    response = _fetch_json(f'{base_url}/chat/completions', payload, headers, timeout=90)
    try:
        raw_content = response['choices'][0]['message']['content'].strip()
        if raw_content.startswith('```'):
            raw_content = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_content)
        data = json.loads(raw_content)
        return data.get('claims', []) if isinstance(data, dict) else data
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise ClaimLabError(f'The claim model returned invalid JSON: {error}') from error


def _heuristic_candidates(source_url, segments):
    now = timezone.now()
    candidates = []
    seen = set()
    last_selected_index = -10
    for index, segment in enumerate(segments):
        text = ' '.join(
            item.get('text', '')
            for item in segments[max(0, index - 1):index + 3]
        )
        text = re.sub(r'\s+', ' ', text).strip()
        if not 40 <= len(text) <= 500 or not FUTURE_LANGUAGE.search(text):
            continue
        if NON_MARKET_LANGUAGE.search(text):
            continue
        if index - last_selected_index <= 3:
            continue
        normalized = text.rstrip('.!')
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        last_selected_index = index
        if not normalized.endswith('?'):
            normalized = f'{normalized}?'
        candidates.append({
            'statement': normalized,
            'excerpt': text,
            'excerpt_start_seconds': int(float(segment.get('start') or 0)),
            'rationale': 'The transcript contains concrete future-facing language that can be reviewed into a binary market.',
            'resolution_criteria': (
                'Resolve YES only if the statement is objectively confirmed by the '
                'listed public resolution source before the resolution deadline; '
                'otherwise resolve NO. A reviewer must make the referenced metric '
                'and threshold explicit before publishing.'
            ),
            'resolution_source_url': source_url,
            'closes_at': now + timedelta(days=14),
            'resolves_at': now + timedelta(days=90),
            'confidence': 0.35,
        })
        if len(candidates) == 5:
            break
    return candidates


def extract_claim_candidates(title, source_url, content, segments):
    llm_error = ''
    try:
        raw_candidates = _extract_with_llm(title, source_url, content)
    except ClaimLabError as error:
        raw_candidates = []
        llm_error = str(error)

    method = f'llm:{getattr(settings, "CLAIM_LLM_MODEL", "qwen")}' if raw_candidates else 'heuristic'
    if not raw_candidates:
        raw_candidates = _heuristic_candidates(source_url, segments)

    normalized = []
    for candidate in raw_candidates[:5]:
        item = _normalize_candidate(candidate, source_url, method)
        if item:
            normalized.append(item)
    return normalized, llm_error
