from django import template
from django.conf import settings

register = template.Library()

class ShowMixpanelInit(template.Node):
    def render(self, context):
        mixpanel_token = getattr(settings, 'MIXPANEL_TOKEN', None)
        if not mixpanel_token:
            return ''.join(["\n",
                "<!-- Mixpanel Analytics is not activated because you haven't set the settings.MIXPANEL_TOKEN variable! -->\n"
                """<!-- start Mixpanel stubs -->\n""",
                """<script type="text/javascript">\n""",
                ShowMixpanelInit.mixpanel_stubs,
                """</script>\n""",
                """<!-- end Mixpanel stubs -->\n"""])

        if 'user' in context and context['user'] and context['user'].is_staff:
            return ''.join(["\n",
                "<!-- Mixpanel Analytics is not activated because you are a staff user! -->\n"
                """<!-- start Mixpanel stubs -->\n""",
                """<script type="text/javascript">\n""",
                ShowMixpanelInit.mixpanel_stubs,
                """</script>\n""",
                """<!-- end Mixpanel stubs -->\n"""])

        return ''.join(["\n",
            """<!-- start Mixpanel -->\n""",
            """<script type="text/javascript">\n""",
            ShowMixpanelInit.mixpanel_init_code,
            """mixpanel.init('""", mixpanel_token, """');\n""",
            """</script>\n""",
            """<!-- end Mixpanel -->\n"""])

    # Snippet taken from mixpanel docs:
    #   https://mixpanel.com/help/reference/javascript
    mixpanel_init_code = ''.join([
        """(function(e,b){if(!b.__SV){var a,f,i,g;window.mixpanel=b;b._i=[""",
        """];b.init=function(a,e,d){function f(b,h){var a=h.split(".");2==""",
        """a.length&&(b=b[a[0]],h=a[1]);b[h]=function(){b.push([h].concat(""",
        """Array.prototype.slice.call(arguments,0)))}}var c=b;"undefined"!""",
        """==typeof d?c=b[d]=[]:d="mixpanel";c.people=c.people||[];c.toStr""",
        """ing=function(b){var a="mixpanel";"mixpanel"!==d&&(a+="."+d);b||""",
        """(a+=" (stub)");return a};c.people.toString=function(){return c.""",
        """toString(1)+".people (stub)"};i="disable track track_pageview t""",
        """rack_links track_forms register register_once alias unregister """,
        """identify name_tag set_config people.set people.set_once people.""",
        """increment people.append people.track_charge people.clear_charge""",
        """s people.delete_user".split(" ");\n""",
        """for(g=0;g<i.length;g++)f(c,i[g]);b._i.push([a,e,d])};b.__SV=1.2""",
        """;a=e.createElement("script");a.type="text/javascript";a.async=!""",
        """0;a.src=("https:"===e.location.protocol?"https:":"http:")+'//cd""",
        """n.mxpnl.com/libs/mixpanel-2.2.min.js';f=e.getElementsByTagName(""",
        """"script")[0];f.parentNode.insertBefore(a,f)}})(document,window.""",
        """mixpanel||[]);\n"""])

    mixpanel_stubs = """
        mixpanel = {
            'push':              function(){},
            'disable':           function(){},
            'track':             function(){},
            'track_links':       function(){},
            'track_forms':       function(){},
            'register':          function(){},
            'register_once':     function(){},
            'unregister':        function(){},
            'identify':          function(){},
            'get_distinct_id':   function(){},
            'alias':             function(){},
            'set_config':        function(){},
            'get_config':        function(){},
            'get_property':      function(){},
            'people': {
                'set':           function(){},
                'set_once':      function(){},
                'increment':     function(){},
                'append':        function(){},
                'track_charge':  function(){},
                'clear_charges': function(){},
                'delete_user':   function(){}
                }
            }
        """


@register.tag
def analytics_mixpanel_init(parser, token):
    return ShowMixpanelInit()
