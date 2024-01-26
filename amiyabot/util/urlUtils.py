import requests

from urllib.parse import urlparse


def is_valid_url(url: str):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org', timeout=3)
        return response.text
    except Exception:
        pass
    return '127.0.0.1'
