from util_requests import request_get
import secrets
import time
from calendar import DateUtil


class Garbage:
    def get_schedule(self, dt_tuple):
        result = []
        
        dt_start = dt_tuple
        dt_end = DateUtil.add_days(dt_start, 1)
        schedule_r = request_get(
            secrets.GARBAGE_SCHEDULE_URL.format(dt_start=DateUtil.date_to_iso(dt_start), dt_end=DateUtil.date_to_iso(dt_end)), headers={
                'x-consumer': secrets.GARBAGE_CONSUMER,
                'content-type': 'application/json',
                'accept': 'application/json',
                'user-agent': 'curl/7.68/0'
            })
        try:
            schedule_json = schedule_r.json()
            for item in schedule_json['items']:
                if 'fraction' not in item: continue
                if 'name' not in item['fraction']: continue
                if 'nl' not in item['fraction']['name']: continue
                dt = DateUtil.iso_to_date(item['timestamp'])
                dt_format = DateUtil.date_to_nice(dt)
                result.append({'type': item['fraction']['name']['nl'], 'date': dt, 'date_format': dt_format })
                
        finally:
            schedule_r.close()
            del schedule_r
        
        return result