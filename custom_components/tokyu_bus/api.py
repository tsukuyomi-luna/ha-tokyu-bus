"""Bounded anonymous read-only requests to an undocumented app API."""
import asyncio
from .model import normalize
BASE = 'https://api.railway.dp.tokyu.co.jp/v2.1/'
UA = 'TokyuLine/4.25.0 (jp.co.tokyu.tokyulinesapplication; build:196; Android SDK 36) '
class BusApi:
    def __init__(self, session, config):
        self.session, self.config = session, config
    async def get(self, path, params):
        async with asyncio.timeout(20):
            async with self.session.get(BASE + path, params=params,
                    headers={'User-Agent': UA, 'Accept': 'application/json'}) as response:
                response.raise_for_status()
                data = await response.json()
                if not isinstance(data, dict):
                    raise ValueError('Invalid response object')
                return data
    async def running(self):
        c = self.config
        raw = await self.get('bus_running', {'from_busstop_id': c['from_stop'],
            'to_busstop_id': c['to_stop'], 'routes': c['route']})
        return normalize(raw, c['route'], c['pole'], c['direction'])
    async def tracking(self, bus):
        keys = ('car_code', 'dia_code', 'route_code', 'updown', 'trip_round_number')
        if any(bus.get(k) in (None, '') for k in keys):
            return None
        c = self.config
        data = await self.get('bus_timetable_tracking', {
            'from_busstop_id': c['from_stop'], 'to_busstop_id': c['to_stop'],
            'car_code': bus['car_code'], 'busdia_code': bus['dia_code'],
            'busroute_code': bus['route_code'], 'updown': bus['updown'],
            'trip_round_number': bus['trip_round_number']})
        if not isinstance(data.get('schedule'), list):
            raise ValueError('Missing tracking schedule')
        return data['schedule']
    async def scheduled(self):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        import jpholiday
        from .model import next_departure
        now = datetime.now(ZoneInfo('Asia/Tokyo'))
        cache_date, cache = getattr(self, '_timetables', (None, {}))
        if cache_date != now.date():
            cache = {}
        self._timetables = (now.date(), cache)
        tables = []
        for offset in (-1, 0, 1):
            day = now.date() + timedelta(days=offset)
            kind = 'HOLIDAY' if day.weekday() == 6 or jpholiday.is_holiday(day) else 'SATURDAY' if day.weekday() == 5 else 'NORMAL'
            if kind not in cache:
                raw = await self.get('bus_route_timetables', {
                    'from_busstop_id': self.config['from_stop'],
                    'to_busstop_id': self.config['to_stop'],
                    'routes': self.config['route'], 'day_of_week': kind})
                if not isinstance(raw.get('timetables'), list):
                    raise ValueError('Missing timetables list')
                cache[kind] = raw['timetables']
            tables.append((day, cache[kind]))
        return next_departure(tables, now, self.config['route'])
