import json
import logging
import urllib.error
import urllib.request

from django.conf import settings


logger = logging.getLogger(__name__)


class AISupportUnavailable(Exception):
    """Raised when the external LLM service cannot be used."""


def _extract_response_text(payload):
    if payload.get('output_text'):
        return str(payload['output_text']).strip()

    if payload.get('text'):
        return str(payload['text']).strip()

    parts = []
    for item in payload.get('output', []):
        for content in item.get('content', []):
            text = content.get('text')
            if text:
                parts.append(text)

    for step in payload.get('steps', []):
        if isinstance(step, dict):
            output = step.get('output')
            if isinstance(output, str):
                parts.append(output)
            elif isinstance(output, dict):
                text = output.get('text') or output.get('output_text')
                if text:
                    parts.append(text)

    for candidate in payload.get('candidates', []):
        content = candidate.get('content', {})
        for part in content.get('parts', []):
            text = part.get('text')
            if text:
                parts.append(text)

    return '\n'.join(parts).strip()


def _build_order_context(order):
    if not order:
        return ''
    return (
        f'Sipariş #{order.id}; durum: {order.get_status_display()}; '
        f'toplam: {order.total_amount} TL; kargo telefonu: {order.phone}.'
    )


def _build_history_text(previous_messages):
    history = []
    for item in previous_messages or []:
        history.append(f'{item.get_sender_type_display()}: {item.message[:600]}')
    return '\n'.join(history[-8:])


def _build_system_instruction():
    return (
        'Sen CoreLogic Store için Türkçe konuşan müşteri destek asistanısın. '
        'Kısa, sakin, çözüm odaklı ve güven veren cevap yaz. '
        'Hukuki kesin hüküm verme, ücret iadesi veya onay sözü verme; gerektiğinde destek ekibinin inceleyeceğini belirt. '
        'Müşteriden gerekiyorsa sipariş numarası, kargo takip numarası, hasarlı ürün fotoğrafı, fatura bilgisi gibi somut bilgi iste. '
        'Cevabı 4-7 cümle arasında tut.'
    )


def _build_support_prompt(ticket_type, subject, message, order=None, previous_messages=None):
    return (
        f'Talep tipi: {ticket_type}\n'
        f'Konu: {subject}\n'
        f'{_build_order_context(order)}\n'
        f'Önceki konuşma:\n{_build_history_text(previous_messages)}\n\n'
        f'Müşteri mesajı:\n{message}'
    )


def generate_gemini_support_reply(ticket_type, subject, message, order=None, previous_messages=None):
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        raise AISupportUnavailable('GEMINI_API_KEY ayarlı değil.')

    body = {
        'model': getattr(settings, 'GEMINI_SUPPORT_MODEL', 'gemini-3.5-flash'),
        'system_instruction': _build_system_instruction(),
        'input': _build_support_prompt(
            ticket_type=ticket_type,
            subject=subject,
            message=message,
            order=order,
            previous_messages=previous_messages,
        ),
        'generation_config': {
            'temperature': getattr(settings, 'GEMINI_SUPPORT_TEMPERATURE', 0.35),
            'max_output_tokens': getattr(settings, 'GEMINI_SUPPORT_MAX_OUTPUT_TOKENS', 420),
        },
    }
    request = urllib.request.Request(
        getattr(settings, 'GEMINI_INTERACTIONS_URL', 'https://generativelanguage.googleapis.com/v1beta/interactions'),
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': api_key,
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=getattr(settings, 'GEMINI_SUPPORT_TIMEOUT', 12)) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning('Gemini destek yanıtı alınamadı: %s', exc)
        raise AISupportUnavailable(str(exc)) from exc

    text = _extract_response_text(payload)
    if not text:
        raise AISupportUnavailable('Gemini boş yanıt döndürdü.')
    return text


def generate_openai_support_reply(ticket_type, subject, message, order=None, previous_messages=None):
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        raise AISupportUnavailable('OPENAI_API_KEY ayarlı değil.')

    prompt = f'{_build_system_instruction()}\n\n{_build_support_prompt(ticket_type, subject, message, order, previous_messages)}'
    body = {
        'model': getattr(settings, 'OPENAI_SUPPORT_MODEL', 'gpt-4.1-mini'),
        'input': prompt,
        'max_output_tokens': getattr(settings, 'OPENAI_SUPPORT_MAX_OUTPUT_TOKENS', 420),
    }
    request = urllib.request.Request(
        getattr(settings, 'OPENAI_RESPONSES_URL', 'https://api.openai.com/v1/responses'),
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=getattr(settings, 'OPENAI_SUPPORT_TIMEOUT', 12)) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning('OpenAI destek yanıtı alınamadı: %s', exc)
        raise AISupportUnavailable(str(exc)) from exc

    text = _extract_response_text(payload)
    if not text:
        raise AISupportUnavailable('OpenAI boş yanıt döndürdü.')
    return text


def generate_external_support_reply(ticket_type, subject, message, order=None, previous_messages=None):
    providers = (
        ('Gemini API', generate_gemini_support_reply),
        ('OpenAI Responses API', generate_openai_support_reply),
    )
    errors = []
    for provider_name, provider in providers:
        try:
            return provider(
                ticket_type=ticket_type,
                subject=subject,
                message=message,
                order=order,
                previous_messages=previous_messages,
            ), provider_name
        except AISupportUnavailable as exc:
            errors.append(f'{provider_name}: {exc}')
    raise AISupportUnavailable(' | '.join(errors) or 'AI sağlayıcı ayarlı değil.')
