import urequests
from calendar import DateUtil
import secrets


class Weather:
    query_string = 'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/huldenberg%20belgium/{dt_start}/{dt_end}?unitGroup=metric&elements=datetime%2Ctempmax%2Ctempmin%2Ctemp%2Cprecip%2Cprecipprob%2Cprecipcover%2Cpreciptype%2Csnow&include=current%2Cdays%2Cfcst&key={api_key}&contentType=json'
    
    def get_weather(self, dt_tuple):
        dt_start = dt_tuple
        dt_end = DateUtil.add_days(dt_start, 1)
        
        result = []
        
        weather_r = urequests.get(
            Weather.query_string.format(dt_start=DateUtil.date_to_iso(dt_start), dt_end=DateUtil.date_to_iso(dt_end), api_key=secrets.WEATHER_API_KEY), headers={})
        try:
            weather_json = weather_r.json()
            i = 1
            for d in weather_json['days']:
                dt = DateUtil.iso_to_date(d['datetime'])
                if i == 1:
                    dt_format = 'Today'
                elif i == 2:
                    dt_format = 'Tomorrow'
                elif i == 3:
                    dt_format = 'Day after'
                else:
                    dt_format = DateUtil.date_to_nice(dt)
                    
                result.append({ 'date': dt, 'dt_format': dt_format,
                                'temp': d['temp'],
                                'tempmin': d['tempmin'],
                                'tempmax': d['tempmax'],
                                'preciptype': d['preciptype'],
                                'precipprob': d['precipprob']
                                })
                i += 1
                
        finally:
            weather_r.close()

        return result
