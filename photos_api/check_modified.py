import calendar
import datetime

from django.utils.http import http_date, parse_http_date_safe
from django.utils.http import parse_etags, quote_etag
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.response import Response

def supports_last_modified(View):
    # Note: session based authentication is explicitly CSRF validated,
    # all other authentication is CSRF exempt.
    @csrf_exempt
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

def supports_etag(View):
    # Note: session based authentication is explicitly CSRF validated,
    # all other authentication is CSRF exempt.
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        def get_not_modified_response(resource_etag):
            if not request.method in ('GET', 'HEAD'):
                return None

            if_none_match = request.META.get("HTTP_IF_NONE_MATCH")
            if if_none_match:
                # There can be more than one ETag in the request, so we
                # consider the list of values.
                try:
                    etags = parse_etags(if_none_match)
                except ValueError:
                    # In case of invalid etag ignore all ETag headers.
                    # Apparently Opera sends invalidly quoted headers at times
                    # (we should be returning a 400 response, but that's a
                    # little extreme) -- this is Django bug #10681.
                    if_none_match = None

            if not if_none_match:
                return None

            if not resource_etag:
                return None

            if resource_etag in etags:
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
                resource_etag = self.get_etag(request, *args, **kwargs)

                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)

                # The ETag header is added!
                response = handler(request, *args, **kwargs)
                response['ETag'] = quote_etag(resource_etag)
            else:
                handler = self.http_method_not_allowed
                response = handler(request, *args, **kwargs)

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    View.dispatch = dispatch
    return View
