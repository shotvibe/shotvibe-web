The app will communicate with the ShotVibe server, which is being currently
development by another team.

All request and response bodies use JSON encoding.

## Authentication

Authentication with the server will be through the use of an Authorization
Token.

The procedure for getting an Authorization Token is:
1.  The user requests to be authorized by submitting his phone number to the
    server.
2.  The server sends an SMS (text message) with a code to the user. The user
    then submits this code to the server and gets back the Authorization Token.

The REST API calls for the above two operations are:
`/auth/authorize_phone_number/` followed by
`/auth/confirm_sms_code/{confirmation_key}/`

Once an Authorization Token is obtained, it should be sent to the server in
every subsequent REST call, using the HTTP header `Authorization`.

Example:

    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96

## Summary of REST API methods

### POST /auth/authorize_phone_number/

Used to request an authorization code via SMS (text message).

### POST /auth/confirm_sms_code/{confirmation_key}/

Used to complete the authorization procedure and obtain an Authorization Token.

### POST /auth/delete_account/

Used to completely delete the user's account and all associated data.

### GET /users/{uid}/

Used to get the user profile data.

### GET /users/{uid}/glance_score/

Used to get the user's glance score

### PATCH /users/{uid}/

Used to set the user profile data.

### PUT /users/{uid}/avatar/

Upload a photo to be used as the user's avatar image.

### GET /albums/

Retrieves all the albums that the user is a member of.

### GET /albums/{aid}/

Retrieves all of the photos that are in an album, and all of the users who are
members of the album.

### GET /albums/public/

Retrieves the id of the public album available to the user.

### POST /photos/upload_request/?num_photos={n}

The user would like to upload `n` photos.

### PUT /photos/upload/{photo_id}/

Upload a single photo. Returns an empty response body.

### POST /photos/upload/{photo_id}/

Alternative method for uploading a single photo. Returns an empty response
body.

### PUT /photos/{photo_id}/comments/{author_id}/{client_msg_id}/

Add a comment to a photo.

### DELETE /photos/{photo_id}/comments/{author_id}/{client_msg_id}/

Delete a comment from a photo.

### PUT /photos/{photo_id}/user_tags/{tagged_user_id}/

Tag a user in a photo.

### DELETE /photos/{photo_id}/user_tags/{tagged_user_id}/

Delete a user tag from a photo.

### PUT /photos/{photo_id}/glance_scores/{author_id}/

Set a glance score of a photo.

### PUT /photos/{photo_id}/glance/

Add a glance emoticon to a photo.

### POST /photos/delete/

Delete photos that a user has uploaded.

### POST /albums/{aid}/

Used to add photos or members to an album.

### PUT /albums/{aid}/name/

Used to change the name of an album.

### POST /albums/{aid}/leave/

Used to leave an album.

### POST /albums/{aid}/view/

Used to mark an album as viewed.

### POST /albums/{aid}/members/

Used to add members to an album.

### GET /albums/{aid}/members/{uid}/phone_number/

Used to get the phone number of an invited member of an album.

### POST /albums/

Used to create a new album.

### POST /register_device_push/

Used to register a mobile device to receive push notifications.

### POST /query_phone_numbers/

Used to query info about phone numbers in a user's phone contact list.

## POST /auth/authorize_phone_number/

Used to request an authorization code via SMS (text message).

The request should include two fields:

*   `phone_number`: The user's phone number
*   `default_country`: ISO 3166-1 two-letter country code (that the user in)

The server will respond with a `confirmation_key`, and will send an SMS text
message to the phone with a confirmation code.

The `confirmation_key` is needed in the next step(along with the code that is
received) in order to complete the authorization.

Example request:

    POST /auth/authorize_phone_number/
    Content-Type: application/json
    Content-Length: 68

    {
        "phone_number": "202-718-1000",
        "default_country": "US"
    }

Example response:

    HTTP 200 OK
    Vary: Accept
    Content-Type: application/json
    Allow: POST, OPTIONS

    {
        "confirmation_key": "64fb97a5a7df19765aebf1c0e70ef229818ca7d5"
    }

## POST /auth/confirm_sms_code/{confirmation_key}/

Used to complete the authorization procedure and obtain an Authorization Token.

The `{confirmation_key}` is the value that was returned from
`/auth/authorize_phone_number/`

The request should include two fields:

*   `confirmation_code`: The code that the user received via SMS (text message)
*   `device_description`: A short human friendly string describing the device,
    to help the user keep track of the devices that he owns that are
    authorized.

For testing purposes, the master code `"6666"` can be used.

The server will respond with one of the following HTTP codes:

*   `200 OK`: The authorization was succesful. The body of the response will
    contain the Authorization Token in the `auth_token` field, and will also contain
    the user's id in the `user_id` field.

*   `403 FORBIDDEN`: The `confirmation_code` that was entered was incorrect.
    The user should be prompted to try again.

*   `410 GONE`: The user waited to long before entering the code, and the
    `confirmation_key` has expired. `/auth/authorize_phone_number` should be
    called again to obtain a new `confirmation_key`

Example request:

    POST /auth/confirm_sms_code/64fb97a5a7df19765aebf1c0e70ef229818ca7d5/
    Content-Type: application/json
    Content-Length: 74

    {
        "confirmation_code": "6666",
        "device_description": "iPhone 5"
    }

Example response:

    HTTP 200 OK
    Vary: Accept
    Content-Type: application/json
    Allow: POST, OPTIONS

    {
        "auth_token": "64fb97a5a7df19765aebf1c0e70ef229818ca7d5",
        "user_id": 22
    }

## POST /auth/delete_account/

This function is very dangerous!

It will delete the user account and all associated data, including:

-   All photos added

-   All albums created, including all of the contained photos, even if other
    users added them!

Request body should be empty.

Will return an empty response on success.

## GET /users/{uid}/

Used to get the user profile data.

Example response:

```
HTTP/1.1 200 OK
Date: Mon, 26 Aug 2013 22:51:34 GMT
Vary: Accept, Host
Content-Type: application/json
Allow: HEAD, GET, PATCH, PUT, OPTIONS

{
    "id": 2,
    "url": "https://api.shotvibe.com/users/2/",
    "nickname": "amanda",
    "avatar_url": "https://shotvibe-avatars-01.s3.amazonaws.com/default-avatar-0064.jpg"
}
```

### GET /users/{uid}/glance_score/

Used to get the user's glance score

Example response:

```
HTTP/1.1 200 OK
Date: Mon, 26 Aug 2013 22:51:34 GMT
Vary: Accept, Host
Content-Type: application/json
Allow: HEAD, GET, OPTIONS

{
    "user_glance_score": 25
}
```

## PATCH /users/{uid}/

Used to set the user profile data.

Currently you can only set the nickname.

The request JSON should be an object containing the field `nickname` set to the
desired nickname.

Example request:

```
PATCH /users/3/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Length: 122

{
    "nickname": "John Smith"
}
```

The response body is the same as for `GET /users/{uid}/`.

## PUT /users/{uid}/avatar/

Upload a photo to be used as the user's avatar image.

Returns an empty response body.

Example request:

```
PUT /users/5/avatar/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Length: 126003

<<< BINARY IMAGE DATA >>>
```

Example response:

```
HTTP 200 OK
Vary: Accept
Content-Type: application/json
Allow: POST, OPTIONS
```

## GET /albums/

Retrieves all the albums that the user is a member of.

This Resource supports the `If-Modified-Since` HTTP header.

Clients should remember the value returned in the `Date` HTTP header, and use
this as the value of `If-Modified-Since` for future requests.

If there have been no updates to the resource, the server will return an empty
response body, and a status code of: `304 Not Modified`

The `etag` field of each album is the same as the HTTP `ETag` header for that
album (see the section below), and can be used to determine which albums have
been updated, so that only those need to be fetched.

The `latest_photos` field contains only the latest two photos from each album.

The `num_new_photos` field contains the number of photos that were added to the
album since the user last reported that he viewed the album. (See `POST
/albums/{aid}/view/`)

The `last_access` field contains the date that the user reported that he last
viewed the album, or `null` if the user has not viewed the album yet. (See
`POST /albums/{aid}/view/`)

Example Request:

    GET /albums/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96

Example response:

    HTTP 200 OK
    Date: Mon, 04 Feb 2013 20:44:12 GMT
    Vary: Accept
    Content-Type: application/json
    Allow: HEAD, GET, POST, OPTIONS

    [
        {
            "id": 5,
            "url": "https://api.shotvibe.com/albums/5/",
            "name": "sprinkling guardhouses segment",
            "creator": {
                "id": 8,
                "url": "https://api.shotvibe.com/users/8/",
                "nickname": "george",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
            },
            "date_created": "2009-10-26T20:53:49Z",
            "last_updated": "2009-11-12T20:20:03Z",
            "etag": "1",
            "num_new_photos": 3,
            "last_access": "2009-11-12T20:03:02Z",
            "latest_photos": [
                {
                    "photo_id": "ea301d20b438dca24ffc7408d990629ca274a961f676e01f2e0be8f3911f1e1f",
                    "photo_url": "https://photos02.shotvibe.com/ea301d20b438dca24ffc7408d990629ca274a961f676e01f2e0be8f3911f1e1f.jpg",
                    "date_created": "2009-11-12T20:20:03Z",
                    "author": {
                        "id": 8,
                        "url": "https://api.shotvibe.com/users/8/",
                        "nickname": "george",
                        "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                    }
                }
            ]
        },
        {
            "id": 9,
            "url": "https://api.shotvibe.com/albums/9/",
            "name": "licorice grindstone's heterosexual crunchier",
            "creator": {
                "id": 8,
                "url": "https://api.shotvibe.com/users/8/",
                "nickname": "george",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
            },
            "date_created": "2008-10-26T20:53:49Z",
            "last_updated": "2009-08-30T08:29:34Z",
            "etag": "2",
            "num_new_photos": 0,
            "last_access": "2009-08-30T08:29:34Z",
            "latest_photos": [
                {
                    "photo_id": "b6cf10999bb7c504dac93f9eeacc75f9c255ab5ab32d882618f80bd22e7ddd5b",
                    "photo_url": "https://photos01.shotvibe.com/b6cf10999bb7c504dac93f9eeacc75f9c255ab5ab32d882618f80bd22e7ddd5b.jpg",
                    "date_created": "2009-08-30T08:29:34Z",
                    "author": {
                        "id": 12,
                        "url": "https://api.shotvibe.com/users/12/",
                        "nickname": "kevin",
                        "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                    }
                },
                {
                    "photo_id": "82551109face69bb53596e73b35d9a5eb2c85e1872ab09112b002a8092a15547",
                    "photo_url": "https://photos01.shotvibe.com/82551109face69bb53596e73b35d9a5eb2c85e1872ab09112b002a8092a15547.jpg",
                    "date_created": "2009-08-25T03:11:24Z",
                    "author": {
                        "id": 670666295,
                        "url": "https://api.shotvibe.com/users/670666295/",
                        "nickname": "x",
                        "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                    }
                }
            ]
        },
        {
            "id": 12,
            "url": "https://api.shotvibe.com/albums/12/",
            "name": "grandad's pep's",
            "creator": {
                "id": 8,
                "url": "https://api.shotvibe.com/users/8/",
                "nickname": "george",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
            },
            "date_created": "2010-10-26T20:53:49Z",
            "last_updated": "2013-02-10T18:57:15.155Z",
            "etag": "3",
            "num_new_photos": 0,
            "last_access": null,
            "latest_photos": [
                {
                    "photo_id": "d3b75ea7338a43983844ffff556288ed0183b9aa9f92e99b5a43fac1d8d2eba0",
                    "photo_url": "https://photos04.shotvibe.com/d3b75ea7338a43983844ffff556288ed0183b9aa9f92e99b5a43fac1d8d2eba0.jpg",
                    "date_created": "2009-09-22T20:21:17Z",
                    "author": {
                        "id": 17,
                        "url": "https://api.shotvibe.com/users/17/",
                        "nickname": "paula",
                        "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                    }
                }
            ]
        },
        {
            "id": 18,
            "url": "https://api.shotvibe.com/albums/18/",
            "name": "Copperfield Olsen's explorations left's reproduce",
            "creator": {
                "id": 8,
                "url": "https://api.shotvibe.com/users/8/",
                "nickname": "george",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
            },
            "date_created": "2009-07-26T20:53:49Z",
            "last_updated": "2009-08-14T13:27:43Z",
            "etag": "8",
            "num_new_photos": 4,
            "last_access": null,
            "latest_photos": [
                {
                    "photo_id": "00a3ae517f40fd6bba76e25e4121a947822787683563950804553e47db54abfd",
                    "photo_url": "https://photos01.shotvibe.com/00a3ae517f40fd6bba76e25e4121a947822787683563950804553e47db54abfd.jpg",
                    "date_created": "2009-08-14T13:27:43Z",
                    "author": {
                        "id": 1791562666,
                        "url": "https://api.shotvibe.com/users/1791562666/",
                        "nickname": "admin",
                        "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                    }
                },
                {
                    "photo_id": "7007dac53f69ffc1b0405ee2876fc986fea1185bed6546df5bd89b8926ed3059",
                    "photo_url": "https://photos03.shotvibe.com/7007dac53f69ffc1b0405ee2876fc986fea1185bed6546df5bd89b8926ed3059.jpg",
                    "date_created": "2009-08-06T11:25:34Z",
                    "author": {
                        "id": 1791562666,
                        "url": "https://api.shotvibe.com/users/1791562666/",
                        "nickname": "admin",
                        "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                    }
                }
            ]
        }
    ]

Another request:

    GET /albums/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    If-Modified-Since: Mon, 04 Feb 2013 20:44:12 GMT

The response:

    HTTP 304 Not Modified

## GET /albums/{aid}/

Retrieves all of the photos that are in an album, and all of the users who are
members of the album.

`{aid}` is the album id.

The HTTP `ETag` should be stored, and on the next request should be used in an
`If-None-Match` HTTP header. If the album has not changed, the server will
return: `304 Not Modified`

The `num_new_photos` field contains the number of photos that were added to the
album since the user last reported that he viewed the album. (See `POST
/albums/{aid}/view/`)

The `last_access` field contains the date that the user reported that he last
viewed the album, or `null` if the user has not viewed the album yet. (See
`POST /albums/{aid}/view/`)

Each object in the `members` array contains the fields:

-   `id`: user ID of the member

-   `nickname`

-   `avatar_url`

-   `invite_status`: Can be one of the following values:

    -   `"joined"`: The member is active and has viewed the album.

    -   `"sms_sent"`: An SMS invitation has been sent to the user, but he has not
        yet installed the app.

    -   `"invitation_viewed"`: The user clicked the SMS and viewed the mobile
        invite page, but he has not yet installed the app.

Example response:

    HTTP 200 OK
    Vary: Accept
    ETag: "2"
    Content-Type: application/json
    Allow: HEAD, GET, POST, OPTIONS

    {
        "id": 5,
        "name": "sprinkling guardhouses segment",
        "creator": {
            "id": 8,
            "url": "https://api.shotvibe.com/users/8/",
            "nickname": "george",
            "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
        },
        "date_created": "2009-10-26T20:53:49Z",
        "last_updated": "2009-11-12T20:20:03Z",
        "num_new_photos": 3,
        "last_access": "2009-11-12T20:03:02Z",
        "members": [
            {
                "id": 1,
                "url": "https://api.shotvibe.com/users/1/",
                "nickname": "admin",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": true,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 2,
                "url": "https://api.shotvibe.com/users/2/",
                "nickname": "amanda",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 5,
                "url": "https://api.shotvibe.com/users/5/",
                "nickname": "daniel",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 6,
                "url": "https://api.shotvibe.com/users/6/",
                "nickname": "emma",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 9,
                "url": "https://api.shotvibe.com/users/9/",
                "nickname": "helen",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 11,
                "url": "https://api.shotvibe.com/users/11/",
                "nickname": "jackie",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 12,
                "url": "https://api.shotvibe.com/users/12/",
                "nickname": "kevin",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 13,
                "url": "https://api.shotvibe.com/users/13/",
                "nickname": "lauren",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 14,
                "url": "https://api.shotvibe.com/users/14/",
                "nickname": "mark",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 15,
                "url": "https://api.shotvibe.com/users/15/",
                "nickname": "nancy",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 17,
                "url": "https://api.shotvibe.com/users/17/",
                "nickname": "paula",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "joined"
            },
            {
                "id": 670666294,
                "url": "https://api.shotvibe.com/users/670666294/",
                "nickname": "x",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "sms_sent"
            },
            {
                "id": 670666295,
                "url": "https://api.shotvibe.com/users/670666295/",
                "nickname": "x",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "sms_sent"
            },
            {
                "id": 670666296,
                "url": "https://api.shotvibe.com/users/670666296/",
                "nickname": "x",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "invitation_viewed"
            },
            {
                "id": 670666297,
                "url": "https://api.shotvibe.com/users/670666297/",
                "nickname": "x",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "sms_sent"
            },
            {
                "id": 1791562667,
                "url": "https://api.shotvibe.com/users/1791562667/",
                "nickname": "testuser",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "invitation_viewed"
            },
            {
                "id": 1791562669,
                "url": "https://api.shotvibe.com/users/1791562669/",
                "nickname": "benny",
                "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png",
                "album_admin": false,
                "added_by_user_id": 1,
                "invite_status": "sms_sent"
            }
        ],
        "photos": [
            {
                "photo_id": "82551109face69bb53596e73b35d9a5eb2c85e1872ab09112b002a8092a15547",
                "photo_url": "https://photos01.shotvibe.com/82551109face69bb53596e73b35d9a5eb2c85e1872ab09112b002a8092a15547.jpg",
                "date_created": "2009-08-25T03:11:24Z",
                "author": {
                    "id": 670666295,
                    "url": "https://api.shotvibe.com/users/670666295/",
                    "nickname": "x",
                    "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                },
                "comments": [],
                "user_tags": [],
                "global_glance_score": 0,
                "my_glance_score_delta": 0,
                "glances": []
            },
            {
                "photo_id": "b6cf10999bb7c504dac93f9eeacc75f9c255ab5ab32d882618f80bd22e7ddd5b",
                "photo_url": "https://photos01.shotvibe.com/b6cf10999bb7c504dac93f9eeacc75f9c255ab5ab32d882618f80bd22e7ddd5b.jpg",
                "date_created": "2009-08-30T08:29:34Z",
                "author": {
                    "id": 12,
                    "url": "https://api.shotvibe.com/users/12/",
                    "nickname": "kevin",
                    "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                },
                "comments": [
                    {
                        "author": {
                            "id": 670666295,
                            "nickname": "x",
                            "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                        },
                        "date_created": "2009-11-12T20:20:03Z",
                        "client_msg_id": 1418582165811,
                        "comment": "I love this photo!",
                    }
                ],
                "user_tags": [
                    {
                        "tagged_user": {
                            "id": 670666295,
                            "nickname": "x",
                            "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                        },
                        "tag_coord_x": 0.56,
                        "tag_coord_y": 0.62
                    }
                ],
                "global_glance_score": 6,
                "my_glance_score_delta": 1,
                "glances": [
                    {
                        "author": {
                            "id": 670666295,
                            "nickname": "x",
                            "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                        },
                        "emoticon_name": "tango_smile.png"
                    }
                ]
            },
            {
                "photo_id": "ea301d20b438dca24ffc7408d990629ca274a961f676e01f2e0be8f3911f1e1f",
                "photo_url": "https://photos02.shotvibe.com/ea301d20b438dca24ffc7408d990629ca274a961f676e01f2e0be8f3911f1e1f.jpg",
                "date_created": "2009-11-12T20:20:03Z",
                "author": {
                    "id": 8,
                    "url": "https://api.shotvibe.com/users/8/",
                    "nickname": "george",
                    "avatar_url": "https://static.shotvibe.com/frontend/img/ndt.png"
                },
                "comments": [],
                "user_tags": [],
                "global_glance_score": 0,
                "my_glance_score_delta": 0,
                "glances": []
            }
        ]
    }

Another example request:

    GET /albums/5/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    If-None-Match: "2"

The response:

    HTTP 304 Not Modified

### GET /albums/public/

Retrieves the id of the public album available to the user.

Example response:

    HTTP 200 OK
    Vary: Accept
    Content-Type: application/json
    Allow: GET, OPTIONS

    {
        "album_id": 5112
    }


## POST /photos/upload_request/?num_photos={n}

The user would like to upload `n` photos.

No request body is necessary.

Example request:

    POST /photos/upload_request/?num_photos=3
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96

Example response:

    HTTP 200 OK
    Vary: Accept
    Content-Type: application/json
    Allow: POST, OPTIONS

    [
        {
            "upload_url": "https://api.shotvibe.com/photos/upload/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/",
            "photo_id": "5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905"
        },
        {
            "upload_url": "https://api.shotvibe.com/photos/upload/906bf4bf2bdf3e80f32660786cd227596b2ffe173d4f3a233f5ab5ad672f87ae/",
            "photo_id": "906bf4bf2bdf3e80f32660786cd227596b2ffe173d4f3a233f5ab5ad672f87ae"
        },
        {
            "upload_url": "https://api.shotvibe.com/photos/upload/19191da2a395424c0abfa9ebfbfdda53cf77eb384125e18d587c63d732baf1be/",
            "photo_id": "19191da2a395424c0abfa9ebfbfdda53cf77eb384125e18d587c63d732baf1be"
        }
    ]

## PUT /photos/upload/{photo_id}/

Upload a single photo. Returns an empty response body.

Example request:

    PUT /photos/upload/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    Content-Length: 126003

    <<< BINARY IMAGE DATA >>>

Example response:

    HTTP 200 OK
    Vary: Accept
    Content-Type: application/json
    Allow: POST, OPTIONS

This method is currently not yet implemented. Use the POST method below
instead.

## POST /photos/upload/{photo_id}/

Alternative method for uploading a single photo. Returns an empty response
body.

The POST should be in the format of an HTML form upload, with the image
uploaded in the field `photo`.

Example request:

    POST /photos/upload/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    Content-Type: multipart/form-data, boundary=AaB03x
    Content-Length: 126003

    --AaB03x
    Content-Disposition: form-data; name="photo"; filename="this-is-ignored.jpg"
    Content-Type: image/jpeg

    <<< BINARY IMAGE DATA >>>
    --AaB03x--

Example response:

    HTTP 200 OK
    Vary: Accept
    Content-Type: application/json
    Allow: POST, OPTIONS

### PUT /photos/{photo_id}/comments/{author_id}/{client_msg_id}/

Add a comment to a photo.

"client_msg_id" should be a 64 bit signed integer value, that is used as a
unique identifier. It is recommended to use the current milliseconds since
epoch (as measured by the user's device).

Any user can add a comment to any photo.

The request JSON should include an object with a field "comment" with a string
value.

The response will be 204 No Content.

Example request:

```
PUT /photos/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/comments/8/1418582165811/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 281

{
    "comment": "I love this photo!"
}
```

### DELETE /photos/{photo_id}/comments/{author_id}/{client_msg_id}/

Delete a comment from a photo.

The request body should be empty.

The response will be 204 No Content.

Example request:

```
DELETE /photos/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/comments/8/1418582165811/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 0

```

### PUT /photos/{photo_id}/user_tags/{tagged_user_id}/

Tag a user in a photo.

The request JSON should include an object with a fields "tag_coord_x" and
"tag_coord_y" with numerical values between 0.0 and 1.0 representing the point
in the image where the tag should be placed.

The response will be 204 No Content.

Example request:

```
PUT /photos/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/user_tags/8/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 281

{
    "tag_coord_x": 0.56,
    "tag_coord_y": 0.62
}
```

### DELETE /photos/{photo_id}/user_tags/{tagged_user_id}/

Delete a user tag from a photo.

The request body should be empty.

The response will be 204 No Content.

Example request:

```
DELETE /photos/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/user_tags/8/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 0

```

### PUT /photos/{photo_id}/glance_scores/{author_id}/

Set a glance score of a photo.

The request JSON should include an object with a field "score_delta" with a
number value of either 1, 0 or -1.

The response will be 204 No Content.

Example request:

```
PUT /photos/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/glance_scores/1418582165811/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 281

{
    "score_delta": 1
}
```

### PUT /photos/{photo_id}/glance/

Add a glance emoticon to a photo.

Any user can glance any photo.

The request JSON should include an object with a field "emoticon_name" with a
string value.

The response will be 204 No Content.

Example request:

```
PUT /photos/5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905/glance/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 281

{
    "emoticon_name": "tango_smile.png"
}
```

## POST /photos/delete/

Delete photos that a user has uploaded.

Only the user that added the photos to the album can delete them.

The request JSON should include an object with a "photos" field that contains
an array of photos that should be deleted.

The response will be 204 No Content.

Example request:

```
POST /photos/delete/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 281

{
    "photos": [
        {
            "photo_id": "5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905"
        },
        {
            "photo_id": "906bf4bf2bdf3e80f32660786cd227596b2ffe173d4f3a233f5ab5ad672f87ae"
        },
        {
            "photo_id": "19191da2a395424c0abfa9ebfbfdda53cf77eb384125e18d587c63d732baf1be"
        }
    ]
}
```

## POST /albums/{aid}/

Used to add photos or members to an album.

`aid` is the album that the photos should be added to.

The request JSON can include the following fields:

*   `add_photos`: Add new photos to the album. All of the photos specified
    should have already been uploaded.

*   `copy_photos` Copy existing photos into this album. All of the photos
*   specified should already exist in some album.

*   `add_members`: Deprecated, use /albums/{aid}/members/ endpoint.

Example request:

    POST /albums/5/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    Content-Type: application/json
    Content-Length: 281

    {
        "add_photos": [
            {
                "photo_id": "5a7e5e6afd698dc0ae2221469fd25b6f9b9941ddab20c90d95f6cba9efa57905"
            },
            {
                "photo_id": "906bf4bf2bdf3e80f32660786cd227596b2ffe173d4f3a233f5ab5ad672f87ae"
            },
            {
                "photo_id": "19191da2a395424c0abfa9ebfbfdda53cf77eb384125e18d587c63d732baf1be"
            }
        ],
        "copy_photos": [
            {
                "photo_id": "3a2ee431e71f2455a3d495d9b8a14d7002a2cf07647ecccc8529b3d28ebb8f0c"
            },
            {
                "photo_id": "4f58cadd39b13b4e5bd1f1939bc1c4533f3919fbc971dc7a0a3e01f50a980578"
            }
        ]
    }

The response returned is the same as for `GET /albums/{aid}/`, with the updated album

### PUT /albums/{aid}/name/

Used to change the name of an album.

`aid` is the album that the user wishes to change.

Only the creator of an album can change its name.

The request JSON should contain a single field, "name", with a string value.

Example request:

    POST /albums/5/name/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    Content-Type: application/json
    Content-Length: 33

    {
        "name": "Birthday Party"
    }


The response will be 204 No Content.

## POST /albums/{aid}/leave/

Used to leave an album.

`aid` is the album that the user wishes to leave.

The request body should be empty.

The response will be 204 No Content.

## POST /albums/{aid}/view/

Used to mark an album as viewed.

`aid` is the album that the user wishes to mark as viewed.

The request JSON should contain a single field, "timestamp", with a date/time value.

The date should be the same as the album's last_updated field at the time of viewing.

Example request:

    POST /albums/5/view/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    Content-Type: application/json
    Content-Length: 37

    {
        "timestamp": "2013-01-22T00:01:02.003Z"
    }


The response will be 204 No Content.

## POST /albums/{aid}/members/

Add new members to the album. Each member is either a user
id, or a phone number. If a phone number is specified, then the user's
country should also be specified, as well as the name of the contact as it
appears in the phone's address book.

Example request:

    POST /albums/5/members/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    Content-Type: application/json
    Content-Length: 324

    {
        "members": [
            {
                "user_id": 4
            },
            {
                "user_id": 6
            },
            {
                "phone_number": "hdff6df",
                "default_country": "US",
                "contact_nickname": "John Smith"
            },
            {
                "phone_number": "212-718-3000",
                "default_country": "US",
                "contact_nickname": "Jane Doe"
            }
        ]
    }

Example response:

    HTTP 200 OK
    Content-Type: application/json

    [
        {
            "success": true
        },
        {
            "success": false,
            "error": "invalid_user_id"
        },
        {
            "success": false,
            "error": "invalid_phone_number"
        },
        {
            "success": true
        }
    ]

### GET /albums/{aid}/members/{uid}/phone_number/

Used to get the phone number of an invited member of an album.

Only the user who invited the member into the album is allowed access.

Example response:

```
HTTP/1.1 200 OK
Date: Mon, 26 Aug 2013 22:51:34 GMT
Vary: Accept, Host
Content-Type: application/json
Allow: HEAD, GET, OPTIONS

{
    "user": {
        "id": 2,
        "url": "https://api.shotvibe.com/users/2/",
        "nickname": "amanda",
        "avatar_url": "https://shotvibe-avatars-01.s3.amazonaws.com/default-avatar-0064.jpg"
    }
    "phone_number": "+12127181111"
}
```

## POST /albums/

Used to create a new album.

The request JSON should have the following 3 required fields:

*   `album_name`: The name of the new album

*   `members`: A list of members that should be added to the album (same format
    as above)

Example request:

    POST /albums/
    Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
    Content-Type: application/json
    Content-Length: 628

    {
        "album_name": "My New Album",
        "members": [
            {
                "user_id": 4
            },
            {
                "user_id": 6
            },
            {
                "phone_number": "212-718-2000",
                "default_country": "US",
                "contact_nickname": "John Smith"
            },
            {
                "phone_number": "212-718-3000",
                "default_country": "US",
                "contact_nickname": "Jane Doe"
            }
        ]
    }

The response returned is the same as for `GET /albums/{aid}/`, with the updated album

## POST /register_device_push/

Used to register a mobile device to receive push notifications.

The request JSON depends on the type the mobile device:

### Android

The request JSON should have the following 3 required fields:

*   `type`: Must be the string "gcm".

*   `app`: Must be a string value with the name of the name of the app.
    Currently it should always be "default".

*   `registration_id`: Must be the device's Registration ID as returned by the
    Android GCM API.

Example request:

```
POST /register_device_push/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 628

{
    "type": "gcm",
    "app": "default",
    "registration_id": "APA91br9Vny8Q45NQ-Y9tSnejA...NmMNUAZNk1_81JaZOBqU6DTcO"
}
```

### iOS

The request JSON should have the following 3 required fields:

*   `type`: Must be the string "apns".

*   `app`: Must be one of the following string values:

    *   "prod": Should be used for the app `com.shotvibe.shotvibe` which will
        be installed in the App Store

    *   "adhoc": Should be used for the app `com.shotvibe.shotvibe.adhoc`.

    *   "dev": Should be used for the app `com.shotvibe.shotvibe.debug` when
        running in development.

*   `device_token`: Must be the device token returned from the iOS Push
    Notifications API, formatted as a lowercase hex-encoded string (See:
    <http://stackoverflow.com/a/12442672>).

Example request:

```
POST /register_device_push/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 628

{
    "type": "apns",
    "app": "prod",
    "device_token": "0f1b4afaa5ead8127e89f83d450b0ba9f61ff05ccc2e7bdde5d76f28b9d0819e"
}
```

### Response

If the registration is successful then response will be `204 No Content`.

## POST /query_phone_numbers/

Used to query info about phone numbers in a user's phone contact list.

The request JSON should contain a `default_country` value as well as a list of
phone contacts. Each phone contact should have a `phone_number` and
`contact_nickname` value.

The response body is an object containing the field `phone_number_details` that
contains an array of results matching the list of phone numbers that were sent.
Each result contains the fields:

-   `phone_type`: Will be either `"mobile"`, `"landline"` or `"invalid"`. If
    this is not `"mobile"` then none of the other fields will be available.

-   `user_id`: Will be a user ID or `null`.

-   `avatar_url`: Will be the url of the avatar of this phone number.

-   `phone_number`: Will be the original phone number, but in a canonical E164
    format.

The app should send the user's contact list to this method, and then app should
display the contact list with the results of this method:

-   Only phone numbers that the server determines are `"mobile"` should be
    displayed to the user.

-   Phone numbers that have a `user_id` value (not `null`) should have a
    "ShotVibe" icon next to them, since they are ShotVibe users.

-   The avatar image of each contact should be displayed. Note that all phone
    numbers have an `avatar_url`, even if they are not registered ShotVibe
    users.

-   Duplicate contacts should not be displayed. It is possible for a user to
    have in his address book contacts that have the same number, but formatted
    differently. For example: "212-718-2002", "2127182002" and "+1 (212) 718
    2002". The server will return all of these will the same value in the
    canonical `phone_number` field, and the app should only display one of
    them.

Example request:

```
POST /query_phone_numbers/
Authorization: Token 01ba4719c80b6fe911b091a7c05124b64eeece96
Content-Type: application/json
Content-Length: 2042

{
    "default_country": "US",
    "phone_numbers": [
        {
            "phone_number": "2127182002",
            "contact_nickname": "John Smith"
        },
        {
            "phone_number": "(212) 718 3003",
            "contact_nickname": "Hardwin Fionnghall"
        },
        {
            "phone_number": "(212) 718 4004",
            "contact_nickname": "Stephan Hendrik"
        },
        {
            "phone_number": "1 (212) 718 2002",
            "contact_nickname": "John Smith Home"
        },
        {
            "phone_number": "4",
            "contact_nickname": "Joe"
        },
    ]
}
```

Example Response:

```
HTTP 200 OK
Vary: Accept
Content-Type: application/json
Allow: POST, OPTIONS

{
    "phone_number_details": [
        {
            "phone_type": "mobile",
            "user_id": 2,
            "avatar_url": "https://www.example.com/john_smith.jpg",
            "phone_number": "+12127182002"
        },
        {
            "phone_type": "landline"
        },
        {
            "phone_type": "mobile",
            "user_id": null,
            "avatar_url": "https://www.example.com/default-avatar-42.jpg",
            "phone_number": "+12127184004"
        },
        {
            "phone_type": "mobile",
            "user_id": 2,
            "avatar_url": "https://www.example.com/john_smith.jpg",
            "phone_number": "+12127182002"
        },
        {
            "phone_type": "invalid"
        }
    ]
}
```
