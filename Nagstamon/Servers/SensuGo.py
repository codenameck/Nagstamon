import sys
import traceback
from Nagstamon.Servers.Generic import GenericServer
from Nagstamon.Objects import (GenericHost, GenericService, Result)
from Nagstamon.Config import conf
from Nagstamon.thirdparty.sensugo_api import SensuGoAPI, SensuGoAPIException

# ckk for debugging
import debugpy
from datetime import datetime 

debugpy.listen(5678)
print("Waiting for debugger attach")
debugpy.wait_for_client()

class SensuGoServer(GenericServer):
    TYPE = 'SensuGo'
    _authentication = 'basic'
    _api_url = ''
    _sensugo_api = None

    def __init__(self, **kwds):
        GenericServer.__init__(self, **kwds)
        self._api_url = conf.servers[self.get_name()].monitor_cgi_url
        self._sensugo_api = SensuGoAPI(self._api_url)

    def init_HTTP(self):
        GenericServer.init_HTTP(self)
        self._setup_sensugo_api()

    def _setup_sensugo_api(self):
        if not self._sensugo_api.has_acquired_token():
            self._sensugo_api.auth(self.username, self.password)

    def _get_status(self):
        response_code, events = self._sensugo_api.get_all_events()
        print(response_code)
        print('ckk _get_status at: ' + str(datetime.now()))

        try:
            self._create_services(events)
        except Exception:
            result, error = self.Error(sys.exc_info())
            print(f'SensuGo response code: {response_code}')
            print(traceback.format_exc())
            return Result(result=result, error=error)
        return Result()
    
    def _create_services(self, events):
        for event in events:
            service = self._parse_event_to_service(event)        
            self._insert_service_to_hosts(service)

    def _parse_event_to_service(self, event): 
        # debugpy.breakpoint()
        service = GenericService()
        service.host = event['entity']['metadata']['namespace']
        service.name = event['check']['metadata']['name']
        service.status = SensuGoAPI.parse_check_status(event['check']['status'])
        service.last_check = datetime.fromtimestamp(int(event['timestamp'])).strftime('%Y-%m-%d %H:%M:%S') 
        service.duration = "05m 15s"
        service.status_information = event['check']['output'] 
        service.attempt = 'xxx'
        service.passiveonly = False
        service.notifications_disabled = False
        service.flapping = False
        service.acknowledged = False
        service.scheduled_downtime = False
        return service
    
    def _insert_service_to_hosts(self, service: GenericService):
        service_host = service.get_host_name()
        if service_host not in self.new_hosts:
            self.new_hosts[service_host] = GenericHost()
            self.new_hosts[service_host].name = service_host
            self.new_hosts[service_host].site = service.site

        self.new_hosts[service_host].services[service.name] = service
