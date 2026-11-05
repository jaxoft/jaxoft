#!/usr/bin/env python3
"""BurgerPortaal-afvalkalenderproef. Alleen lezen; geen MQTT of HA-schrijfacties."""
import getpass
import http.cookiejar
import json
from datetime import datetime, timezone
import re
import sys
import urllib.error
import urllib.request

BASE = 'https://21burgerportaal.mendixcloud.com/xas/'
ORGANISATIE = '452048812597352613'


def main():
    postcode = (sys.argv[1] if len(sys.argv) > 1 else input('Postcode: ')).strip().replace(' ', '').upper()
    if not re.fullmatch(r'[1-9][0-9]{3}[A-Z]{2}', postcode):
        sys.exit('Ongeldige postcode.')
    huisnummer = (sys.argv[2] if len(sys.argv) > 2 else input('Huisnummer: ')).strip()
    if not huisnummer.isdigit():
        sys.exit('Ongeldig huisnummer. Huisletter/toevoeging volgt later.')

    cookiejar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookiejar)
    )
    with opener.open(
    "https://21burgerportaal.mendixcloud.com/p/breda/landing/",
    timeout=30
    ) as response:
        print("Website geopend:", response.status)
    def call(data, csrf=None):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
                   'X-Requested-With': 'XMLHttpRequest'}
        if csrf:
            headers['X-CSRF-Token'] = csrf
        if data.get('action') == 'runtimeOperation':
            print('=== Requeststructuur ===')
            print('JSON-velden:', sorted(data.keys()))
            print('Headers:', sorted(headers.keys()))
            print('CSRF aanwezig:', bool(headers.get('X-CSRF-Token')))
            print('Aantal cookies:', len(cookiejar))
            print('Cookie-namen:', sorted(cookie.name for cookie in cookiejar))
        req = urllib.request.Request(BASE, data=json.dumps(data).encode(), headers=headers)
        if data.get('action') == 'runtimeOperation':
            test_req = urllib.request.Request(BASE)
            cookiejar.add_cookie_header(test_req)
            cookie_header = test_req.get_header('Cookie', '')

            print('Sessiecookies meegestuurd:',
                '__Host-XASSESSIONID=' in cookie_header)
            print('XASID meegestuurd:',
                'xasid=' in cookie_header)
        with opener.open(req, timeout=30) as response:
            return json.load(response)


    def operation(op, params, csrf, objects=None, changes=None):
        payload = {
            'action': 'runtimeOperation',
            'operationId': op,
            'params': params,
            'changes': changes or {},
            'objects': objects or [],
            'profiledata': {}
        }

        if op == 'eHvo973pnl2stzmXI8SpjA':
            payload['options'] = {}

        elif op == '4pSmQ7SgUlCQ8BbbusQIRg':
            payload['validationGuids'] = [
                params['link']['guid'],
                params['helper']['guid']
            ]

        print('=== Mendix-operatie ===')
        print('Operation ID:', op)
        print('JSON-velden:', sorted(payload.keys()))
        print('Aantal objecten:', len(payload['objects']))
        print('Aantal wijzigingen:', len(payload['changes']))

        return call(payload, csrf)

    try:
        sessie = call({
            'action': 'get_session_data',
            'params': {
                'offline': False,
                'referrer': 'https://21burgerportaal.mendixcloud.com/p/breda/landing/',
                'deviceType': 'Desktop',
                'timezoneoffset': -60,
                'timezoneId': 'Europe/Amsterdam',
                'preferredLanguages': ['nl-NL', 'nl'],
                'version': 2
            }
        })
        csrf = sessie['csrftoken']
        print('\n=== Referentiegegevens ===')
        print('Gebruiker heeft hash:', bool(sessie['user'].get('hash')))
        print('Gebruikerstype:', sessie['user'].get('objectType'))
        print('Sessieobject-ID aanwezig:', bool(sessie.get('sessionObjectId')))
        print('Sessiereferentie in objects:',
            any(o.get('guid') == sessie.get('sessionObjectId')
                for o in sessie.get('objects', [])))
        initial = operation('eHvo973pnl2stzmXI8SpjA', {}, csrf)
        for op_id, with_profile in [
            ('u3tnrUgauVu5yVB8ZIsrfQ', True),
            ('zTRi6Qq/Clu2QVLGpzbL2w', False),
            ]:
            payload = {
                'action': 'runtimeOperation',
                'operationId': op_id,
                'params': {},
                'options': {},
                'changes': {},
                'objects': []
            }
            if with_profile:
                payload['profiledata'] = {}

            call(payload, csrf)
            print('Extra initialisatie geslaagd:', op_id)    
        objs = {o['objectType']: o for o in initial.get('objects', [])}
        names = ['Burger_Applicatie.sessionData', 'Burger_Applicatie.link', 'Burger_Applicatie.helper']
        if not all(n in objs for n in names):
            sys.exit('Initialisatie incompleet: ' + ', '.join(n for n in names if n not in objs))
        sd, link, helper = (objs[n] for n in names)
        print('Initialisatie: 3 vereiste objecten ontvangen')
        print('Mendix-gebruiker aanwezig:', bool(sessie.get('user', {}).get('guid')))
        print('Mendix-sessie aanwezig:', bool(sessie.get('sessionObjectId')))
        # De referenties gebruiken uitsluitend GUIDs uit de nieuwe sessie.
        # Hashes uit een oude HAR mogen niet worden hergebruikt.
        # Gebruik uitsluitend referentiehashes uit de actuele sessie.
        # Een algemene objecthash (v2:...) is geen referentiehash.
        initial_changes = initial.get('changes') or {}

        def reference_change(obj, attribute, value):
            ref = (initial_changes.get(obj['guid']) or {}).get(attribute)
            if not isinstance(ref, dict) or not ref.get('hash'):
                raise ValueError(
                    'Referentiehash ontbreekt in initialisatie voor '
                    + obj['objectType'] + '.' + attribute
                )
            return {'hash': ref['hash'], 'value': value}

        changes = {
            sd['guid']: {
                'token': {'value': ORGANISATIE},
                'municipality': {'value': 'Breda'},
                'Burger_Applicatie.sessionData_User': reference_change(
                    sd, 'Burger_Applicatie.sessionData_User', sessie['user']['guid']),
                'Burger_Applicatie.sessionData_Session': reference_change(
                    sd, 'Burger_Applicatie.sessionData_Session', sessie['sessionObjectId']),
            },
            link['guid']: {
                '_type': {'value': 'address'},
                'name': {'value': 'address'},
                'rel': {'value': 'address'},
                'Burger_Applicatie.link_helper': reference_change(
                    link, 'Burger_Applicatie.link_helper', helper['guid']),
                'href': {'value': ''},
            },
            helper['guid']: {
                'Burger_Applicatie.link_helper': reference_change(
                    helper, 'Burger_Applicatie.link_helper', link['guid']),
                'adres': {'value': postcode.lower()},
                'housenummer': {'value': huisnummer},
            },
        }
        print('Alle vier referentiehashes uit initialisatie opgehaald')
        print('\n=== Objecten en wijzigingen ===')

        for obj in (sd, link, helper):
            guid = obj['guid']
            print('\nObjecttype:', obj['objectType'])
            print('Hash aanwezig:', bool(obj.get('hash')))
            print('Beschikbare attributen:',
                sorted(obj.get('attributes', {}).keys()))
            print('Gewijzigde attributen:',
                sorted(changes.get(guid, {}).keys()))
        result = operation('4pSmQ7SgUlCQ8BbbusQIRg',
                           {'link': {'guid': link['guid']}, 'helper': {'guid': helper['guid']}},
                           csrf, [sd, link, helper], changes)
        types = sorted(set(o.get('objectType', '') for o in result.get('objects', [])))
        print('Adresaanvraag uitgevoerd')
        print('Objecten ontvangen:', len(result.get('objects', [])))
        print('ResultSet_Groups:', sum(o.get('objectType') == 'Burger_Applicatie.ResultSet_Groups'
                                        for o in result.get('objects', [])))
        print('Objecttypen:', ', '.join(types))
        if result.get('error'):
            print('Backend gaf een foutobject terug (details bewust verborgen).')

        # Stap 2: haal het actuele adres-ID uit de URL in het adresresultaat.
        # Het is een API-adres-ID, niet de Mendix-object-GUID.
        address_ids = set()
        for obj in result.get('objects', []):
            if obj.get('objectType') != 'Burger_Applicatie.Adres':
                continue
            url = obj.get('attributes', {}).get('_selfURL', {}).get('value') or ''
            match = re.search(r'/adressen/(\d+)(?:/|$)', url)
            if match:
                address_ids.add(match.group(1))
        if len(address_ids) != 1:
            raise ValueError('Geen eenduidig adres-ID gevonden in de adresrespons')
        aid = address_ids.pop()
        print('Adres-ID gevonden:', True)

        # Stap 3: maak de kalender-helper aan via de browseroperatie.
        # sessionData blijft hetzelfde oorspronkelijke Mendix-object.
        helper_result = operation(
            'Jw37Ngf6CVKdw0n/pu8QLg', {}, csrf,
            objects=[sd], changes={sd['guid']: changes[sd['guid']]}
        )
        calendar_helpers = [o for o in helper_result.get('objects', [])
                            if o.get('objectType') == 'Burger_Applicatie._Helper']
        if len(calendar_helpers) != 1:
            raise ValueError('Kalender-helper niet ontvangen')
        calendar_helper = calendar_helpers[0]
        helper_changes = helper_result.get('changes', {}).get(calendar_helper['guid'], {})
        for attr in ('Burger_Applicatie._Helper_Session', 'municipality'):
            if not (isinstance(helper_changes.get(attr), dict)
                    and helper_changes[attr].get('hash')):
                raise ValueError('Kalender-referentiehash ontbreekt: ' + attr)
        print('Kalender-helper aangemaakt')

        # Stap 4: kalenderdata ophalen. Dit is de structuur van de HAR-aanvraag.
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        calendar_changes = {
            sd['guid']: changes[sd['guid']],
            calendar_helper['guid']: {
                'JaarNummer': {'value': str(now.year)},
                'MaandNummer': {'value': str(now.month)},
                'Burger_Applicatie._Helper_Session': {
                    'hash': helper_changes['Burger_Applicatie._Helper_Session']['hash'],
                    'value': sessie['sessionObjectId']
                },
                'DateBeginMaand': {'value': int(month_start.timestamp() * 1000)},
                'municipality': {
                    'hash': helper_changes['municipality']['hash'],
                    'value': 'Breda'
                },
            }
        }
        calendar_payload = {
            'action': 'runtimeOperation',
            'operationId': '/ZwKTnNq5l+ADDSOpMPdFw',
            'params': {'aid': {'value': aid}},
            'validationGuids': [],
            'changes': calendar_changes,
            'objects': [sd, calendar_helper],
            'profiledata': {}
        }
        print('Kalender opvragen voor:', now.year, now.month)
        calendar = call(calendar_payload, csrf)
        planning = [o for o in calendar.get('objects', [])
                    if o.get('objectType') == 'Burger_Applicatie.FractieSet_Planning']
        print('Planningsobjecten ontvangen:', len(planning))
        if not planning:
            print('Geen planningsobjecten ontvangen; controleer de kalenderrespons.')
        else:
            entries = set()
            for obj in planning:
                attrs = obj.get('attributes', {})
                def val(key):
                    return (attrs.get(key) or {}).get('value')
                day = val('MatchKey')
                fraction = val('FractieOmschrijving')
                if day and fraction:
                    try:
                        date_iso = datetime.strptime(day, '%d-%m-%Y').date().isoformat()
                    except ValueError:
                        date_iso = str(day)
                    entries.add((date_iso, str(fraction)))
            print('\n=== Afvalkalender ===')
            for day, fraction in sorted(entries):
                print(day, '-', fraction)
            print('Unieke ophaalmomenten:', len(entries))

    except urllib.error.HTTPError as exc:
        print('HTTP-fout:', exc.code)
        try:
            body = exc.read().decode('utf-8', errors='replace')
            info = json.loads(body)
            print('Foutantwoordvelden:', sorted(info) if isinstance(info, dict) else type(info).__name__)
            if isinstance(info, dict):
                description = info.get('description')
                if isinstance(description, str):
                    print('Foutomschrijving:', description)
            if isinstance(info, dict):
                for key in ('error', 'errorCode', 'code', 'type'):
                    if key in info:
                        value = info[key]
                        print(key + ' type:', type(value).__name__)
                        if key == 'type' and isinstance(value, str):
                            print('Foutcategorie:', value[:100])
                        if isinstance(value, dict):
                            print(key + ' velden:', sorted(value))
                result = info.get('result')
                print('Resultaatsoort:', type(result).__name__)
                if isinstance(result, dict):
                    print('Resultaatvelden:', sorted(result))
                elif isinstance(result, list):
                    print('Aantal resultaatelementen:', len(result))
                    print('Elementtypen:', [type(x).__name__ for x in result[:5]])
                elif isinstance(result, str):
                    # Geen ruwe backendtekst tonen: kan adres, token of sessiegegevens bevatten.
                    print('Resultaatlengte:', len(result))
                    for term in ('invalid', 'hash', 'object', 'session', 'access', 'permission',
                                 'unauthorized', 'csrf', 'microflow', 'parameter', 'reference', 'error'):
                        print('Bevat ' + term + ':', term in result.lower())
        except Exception:
            print('Foutantwoord is geen leesbare JSON (inhoud verborgen).')
    except ValueError as exc:
        print('Controlefout:', str(exc))
    except Exception as exc:
        # Voorkom uitlekken van adres- of sessiegegevens in foutmeldingen.
        print('Fouttype:', type(exc).__name__)

if __name__ == '__main__':
    main()
