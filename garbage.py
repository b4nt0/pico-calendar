import urequests
import secrets
import time
from calendar import DateUtil


class Garbage:
    def __init__(self):
        self.token = None

    def get_token(self):
        token_r = urequests.get(secrets.GARBAGE_TOKEN_URL, headers={
            'x-consumer': secrets.GARBAGE_CONSUMER,
            'x-secret': secrets.GARBAGE_SECRET
            })
        try:
            print(token_r.json())
            self.token = str(token_r.json()['accessToken'])
        finally:
            token_r.close()
            del token_r
            
        return self.token
    
    def get_schedule(self, dt_tuple):
        result = []
        
        if self.token is None:
            self.get_token()
            
        dt_start = dt_tuple
        dt_end = DateUtil.add_days(dt_start, 7)
        schedule_r = urequests.get(
            secrets.GARBAGE_SCHEDULE_URL.format(dt_start=DateUtil.date_to_iso(dt_start), dt_end=DateUtil.date_to_iso(dt_end)), headers={
                'x-consumer': secrets.GARBAGE_CONSUMER,
                'Authorization': self.token
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