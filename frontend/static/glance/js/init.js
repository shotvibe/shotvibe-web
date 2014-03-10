skel.init({
    prefix: '/static/glance/css/style',
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

    }

    // Alt Header
    $altHeader.addClass('inactive');

    $window.scroll(function() {

        if ($window.scrollTop() > $features.offset().top - 100)
            $altHeader.removeClass('inactive');
        else
            $altHeader.addClass('inactive');

    });

});
