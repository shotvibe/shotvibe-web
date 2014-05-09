function startSlideshow(url) {
    var photo = document.getElementById('photo');

    function refresh() {
        photo.src = url + '?' + (new Date().getTime()) + ';' + Math.random();
    }

    var REFRESH_INTERVAL = 5000;
    window.setInterval(refresh, REFRESH_INTERVAL);

    refresh();
}
