// This is used for the "prefix" variable below. Needed for figuring out where
// to find css files relative to this source js file.
//
// See this for reference:
//     http://stackoverflow.com/questions/984510/what-is-my-script-src-url/984656#984656
var scriptSource = (function() {
    var scripts = document.getElementsByTagName('script'),
        script = scripts[scripts.length - 1];

    if (script.getAttribute.length !== undefined) {
        return script.getAttribute('src')
    }

    return script.getAttribute('src', 2)
}());

var staticPrefix = scriptSource.substr(0, scriptSource.lastIndexOf('/') - 'js'.length);

skel.init({
    prefix: staticPrefix + 'css/style',
    resetCSS: true,
    boxModel: 'border',
    useOrientation: true,
    breakpoints: {
        'normal': {
            range: '*',
            containers: 960,
            viewport: 'width=1040,user-scalable=no',
            grid: {
                gutters: 40
            }
        },
        'mobile': {
            range: '-640',
            containers: '90%',
            lockViewport: true,
            grid: {
                gutters: 20,
                collapse: true
            }
        }
    }
});

jQuery.fn.n33_formerize=function(){var _fakes=new Array(),_form = jQuery(this);_form.find('input[type=text],textarea').each(function() { var e = jQuery(this); if (e.val() == '' || e.val() == e.attr('placeholder')) { e.addClass('formerize-placeholder'); e.val(e.attr('placeholder')); } }).blur(function() { var e = jQuery(this); if (e.attr('name').match(/_fakeformerizefield$/)) return; if (e.val() == '') { e.addClass('formerize-placeholder'); e.val(e.attr('placeholder')); } }).focus(function() { var e = jQuery(this); if (e.attr('name').match(/_fakeformerizefield$/)) return; if (e.val() == e.attr('placeholder')) { e.removeClass('formerize-placeholder'); e.val(''); } }); _form.find('input[type=password]').each(function() { var e = jQuery(this); var x = jQuery(jQuery('<div>').append(e.clone()).remove().html().replace(/type="password"/i, 'type="text"').replace(/type=password/i, 'type=text')); if (e.attr('id') != '') x.attr('id', e.attr('id') + '_fakeformerizefield'); if (e.attr('name') != '') x.attr('name', e.attr('name') + '_fakeformerizefield'); x.addClass('formerize-placeholder').val(x.attr('placeholder')).insertAfter(e); if (e.val() == '') e.hide(); else x.hide(); e.blur(function(event) { event.preventDefault(); var e = jQuery(this); var x = e.parent().find('input[name=' + e.attr('name') + '_fakeformerizefield]'); if (e.val() == '') { e.hide(); x.show(); } }); x.focus(function(event) { event.preventDefault(); var x = jQuery(this); var e = x.parent().find('input[name=' + x.attr('name').replace('_fakeformerizefield', '') + ']'); x.hide(); e.show().focus(); }); x.keypress(function(event) { event.preventDefault(); x.val(''); }); });  _form.submit(function() { jQuery(this).find('input[type=text],input[type=password],textarea').each(function(event) { var e = jQuery(this); if (e.attr('name').match(/_fakeformerizefield$/)) e.attr('name', ''); if (e.val() == e.attr('placeholder')) { e.removeClass('formerize-placeholder'); e.val(''); } }); }).bind("reset", function(event) { event.preventDefault(); jQuery(this).find('select').val(jQuery('option:first').val()); jQuery(this).find('input,textarea').each(function() { var e = jQuery(this); var x; e.removeClass('formerize-placeholder'); switch (this.type) { case 'submit': case 'reset': break; case 'password': e.val(e.attr('defaultValue')); x = e.parent().find('input[name=' + e.attr('name') + '_fakeformerizefield]'); if (e.val() == '') { e.hide(); x.show(); } else { e.show(); x.hide(); } break; case 'checkbox': case 'radio': e.attr('checked', e.attr('defaultValue')); break; case 'text': case 'textarea': e.val(e.attr('defaultValue')); if (e.val() == '') { e.addClass('formerize-placeholder'); e.val(e.attr('placeholder')); } break; default: e.val(e.attr('defaultValue')); break; } }); window.setTimeout(function() { for (x in _fakes) _fakes[x].trigger('formerize_sync'); }, 10); }); return _form; };

jQuery.fn.n33_scrolly = function() {
    var bh = jQuery('body,html'), t = jQuery(this);

    t.click(function(e) {
        var h = jQuery(this).attr('href'), target;

        if (h.charAt(0) == '#' && h.length > 1 && (target = jQuery(h)).length > 0)
        {
            var x = target.offset().top - ( ($(window).height() - target.outerHeight()) / 2);
            var pos = Math.max(x, 0);
            e.preventDefault();
            bh
                .stop(true, true)
                .animate({ scrollTop: pos }, 'slow', 'swing');
        }
    });

    return t;
};

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(function() {

    var $window = $(window),
        $wrapper = $('#wrapper'),
        $body = $('body'),
        $altHeader = $('#alt-header'),
        $banner = $('#banner'),
        $go_default = $('li.default'),
        $go_ios = $('li.ios'),
        $go_android = $('li.android'),
        $download = $('#download'),
        $features = $('.feature.first'),
        $button_open = $('.button.download'),
        $button_close = $download.find('.closer');

    // Disable CSS animation until loading is complete
    $body.addClass('loading');
    $wrapper.fadeTo(0, 0.0001);

    $window.load(function() {
        window.setTimeout(function() {
            $body.removeClass('loading');
            $wrapper.fadeTo(600, 1.0);
        }, 100);

        $window.trigger('scroll');
    });

    // Forms
    if (skel.vars.IEVersion < 10)
        $('form').n33_formerize();

    // Download

    // Hide all download buttons
    $go_default.hide();
    $go_ios.hide();
    $go_android.hide();

    // iOS or Android device?
    if (skel.vars.deviceType == 'ios'
    ||  skel.vars.deviceType == 'android') {

        // Mark as inactive
        $body.addClass('inactive');

        // Show download button for appropriate OS type
        switch (skel.vars.deviceType) {
            case 'ios':
                $go_ios.show();
                break;

            case 'android':
                $go_android.show();
                break;

            default:
                $go_default.show();
                break;
        }

    }
    // Other OS
    else {

        // Show default download button
        $go_default.show();

        // Mark as inactive (if we're using IE > 8)
        if (skel.vars.IEVersion > 8)
            $body.addClass('inactive');

        // Events
        $button_open
            .click(function(e) {
                $body.removeClass('inactive');
            })
            .n33_scrolly();

        $button_close.click(function(e) {
            $body.addClass('inactive');
            return true;
        });

        $("#sms-error").hide();
        $("#sms-success").hide();
        $("#sms-throttle").hide();

        $('#sms-send').click(function() {
            var country_code = $('#country_code').val();
            var phone_number = $('#phone_number').val();

            if (!phone_number) {
                $('#phone_number').focus();
                return false;
            }

            $('#sms-send').attr('disabled', 'disabled');
            $("#sms-error").hide();

            $.ajax('/request_sms/', {
                contentType: 'application/json',
                type: 'POST',
                data: JSON.stringify({
                    phone_number: phone_number,
                    default_country: country_code
                }),
                beforeSend: function(xhr) {
                    xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
                },
                success: function() {
                    // success
                    $("#sms-form").hide();
                    $("#sms-success").show();
                },
                error: function(xhr, status, error) {
                    if (xhr.status == 429) {
                        // throttled
                        $("#sms-form").hide();
                        $("#sms-throttle").show();
                    }
                    else if (xhr.status == 400) {
                        // bad request
                        $("#sms-error").show();
                    }
                    else {
                        // error, try again?
                    }

                    $('#sms-send').removeAttr('disabled');
                }
            });

            return false;
        });

    }

    // Alt Header
    $altHeader.addClass('inactive');

    $window.scroll(function() {

        if ($window.scrollTop() > $features.offset().top - 100)
            $altHeader.removeClass('inactive');
        else
            $altHeader.addClass('inactive');

    });

    // Homepage.
    if ($body.hasClass('homepage')) {

        // Video banner.
        if (!skel.vars.isMobile
                && !skel.isActive('mobile')) {
            var $banner = $('#banner'),
                $video = $('<video loop="loop" autoplay="autoplay" preload="auto"'
                    + 'poster="' + staticPrefix + 'images/banner.png">'
                    + '<source src="' + staticPrefix + 'videos/video.webm" type="video/webm">'
                    + '<source src="' + staticPrefix + 'videos/video.mp4" type="video/mp4">'
                    + '</video>');

            $banner.css('background-image', 'none');

            $video
                .fadeTo(0, 0)
                .appendTo($banner);

            $window
                .on('load', function() {
                    $video.fadeTo(3000, 1);
                    $video[0].play();
                });
        }
    }

});
