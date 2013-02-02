import calendar
import datetime

from django.utils.http import http_date, parse_http_date_safe

from rest_framework import status
from rest_framework.response import Response

def supports_last_modified(View):
    def dispatch(self, request, *args, **kwargs):
        def get_not_modified_response():
            if not request.method in ('GET', 'HEAD'):
                return None

            if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE")
            if if_modified_since:
                if_modified_since = parse_http_date_safe(if_modified_since)

            if not if_modified_since:
                return None

            dt = self.last_modified(request, *args, **kwargs)
            if not dt:
                return None

            res_last_modified =  calendar.timegm(dt.utctimetuple())
            if res_last_modified and res_last_modified < if_modified_since:
                return Response(status=status.HTTP_304_NOT_MODIFIED)
            else:
                return None

        # Code adapted from the original dispatch method:

        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.headers = self.default_response_headers  # deprecate?

        try:
            self.initial(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                not_modified_response = get_not_modified_response()
                if not_modified_response:
                    response = not_modified_response
                else:
                    handler = getattr(self, request.method.lower(),
                                      self.http_method_not_allowed)

                    # The Date header is added!
                    current_time = datetime.datetime.now()
                    response = handler(request, *args, **kwargs)
                    response['Date'] = http_date(calendar.timegm(current_time.utctimetuple()))
            else:
                handler = self.http_method_not_allowed
                response = handler(request, *args, **kwargs)

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    View.dispatch = dispatch
    return View
