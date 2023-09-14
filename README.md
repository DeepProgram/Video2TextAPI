
# Reuv Play Backend API

Backend Of ReuvPlay Frontend


## Frontend
Setup the frontend to visualize the backend data properly
[ReuvPlay Backend API](https://github.com/DeepProgram/Video2TextWeb.git)
## Prerequisites
In order to be able to run Push locally you will need to have docker and docker-compose installed on your machine. You can install them by following instructions in these links:
- https://docs.docker.com/engine/install/
- https://docs.docker.com/compose/install/

## Getting Started
1.Clone the repo to your machine.

`git clone https://github.com/DeepProgram/Video2TextAPI.git`

2.Create a folder named **content** and under that folder create 4 more folders
- **audio**
- **segment**
- **thumbnail**
- **video**

3.Add database credential in **config/settings.py**
```bash
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "db",
        "PORT": 5432,
    }
}
```
4.Build docker image

`docker-compose -f docker-compose.local.yaml build`

5.Run docker container

`docker-compose -f docker-compose.local.yaml up`

6.Apply database migration

`docker-compose exec -it django_conatiner_v2tapi bash`

`python manage.py makemigrations`

`python manage.py migrate`

7.Create a superuser to be able to acces the admin panel

`docker-compose exec -it django_conatiner_v2tapi bash`

`python manage.py createsuperuser`
## Features

- User
    - Models
        - **UserData**
            ```bash
            user_id = models.UUIDField()
            email = models.TextField()
            password = models.TextField()
            full_name = models.TextField()
            user_level = models.IntegerField()  # 1 -> Pro, 2 -> Pro Plus
            join_epoch_time = models.IntegerField(default=0)  # Epoch Time In Seconds
            ```
    - Views
        - **signup** view accepts json of email, password, full_name, account_type data and add user in db
            ```json
            {
                "email" : "root@root.com",
                "password": "1234",
                "full_name": "Root User",
                "account_type": 2
            }
        - **login** view accepts json of email, password and it gets verified by the data of db
            ```json
            {
                "email" : "root@root.com",
                "password" : "1234"
            }
    - Tasks
        - **is_user_already_exist** function takes email as input and checks if email is already registered or not
        - **task_save_user_credential_in_db** function takes email, password, full_name, account_type and save it to database
        - **task_verify_login** function takes email, password and verify these data from database
        - **task_generate_jwt_token** takes user_id as input and generate **JWT (Json Web Token)** and returns it
        - **task_verify_token** takes jwt_token as input and verify it and return its result

- Video
    - Model
        - **VideoData**
            ```bash
            video_id = models.UUIDField()
            video_title = models.TextField()
            video_duration = models.IntegerField()
            platform = models.TextField()
            channel_id = models.TextField()
            channel_name = models.TextField()
            video_url = models.TextField()
            local_video_path = models.TextField(default="")
            local_thumbnail_path = models.TextField(default="")
            is_video_processed = models.BooleanField(default=False)
            video_processed_by = models.TextField(default="Reuv Play")
            video_processed_on = models.IntegerField(default=0)  # Epoch Time In Seconds
            ```
        - **RequestedVideo**
            ```bash
            request_id = models.UUIDField()
            video_data = models.ForeignKey(VideoData, on_delete=models.CASCADE)
            requested_by = models.ForeignKey(UserData, on_delete=models.CASCADE)
            is_video_processed = models.BooleanField()
            queue_position = models.IntegerField()
            request_epoch_time = models.IntegerField()
            request_completed_epoch_time = models.IntegerField(default=0)
            ```
        - **VideoSegments**
            ```bash
            clip_id = models.UUIDField()
            video_data = models.ForeignKey(VideoData, on_delete=models.CASCADE)
            start_time = models.FloatField()
            end_time = models.FloatField()
            text = models.TextField()
            ```
        - **ProcessVideoSession**
            ```bash
            session_id = models.UUIDField()
            user_data = models.ForeignKey(UserData, on_delete=models.CASCADE)
            session_creation_time = models.IntegerField()
            session_end_time = models.IntegerField()
            status = models.TextField()
            progress = models.IntegerField()
            video_data = models.ForeignKey(VideoData, on_delete=models.CASCADE)
            ```
    - Views
        - **search_video** accepts platform and video_url as json data and validate youtube or twitch url and get the video info
            ```json
            {
                "platform" : "youtube",
                "video_url" : "https://www.youtube.com/watch?v=U0ziGKtIBT0",
            }
        - **request_for_process** accepts platform and video_url as json data and add the video info in database in RequestedVideo table
        - **get_requested_video_info** accpets JWT token in request header from client and verify it and gets the user_id and search by it in RequestedVideo table and get info
        - **download_and_process_video** accepts platform and video_url as json data and add a background task using celery and start the video processing
        - **get_process_video_processing_status** accpets JWT token in request header from client and verify it and gets the user_id and search by it ProcessVideoSession table for the latest video processing status of the user
        - **get_process_video_completed_status** accpets JWT token and get user_id from it and search it in VideoData table and checks for the video_info processed by the user
        - **get_all_videos** returns all processed video in json response
            ```json
            {
                "hint": "got_all_videos",
                "code": 1,
                "data": [
                    {
                        "video_id": "566eb263-1e8d-477b-a455-b7e0f24a0ba2",
                        "title": "Hiding Grenades in Fireplaces lol (DayZ)",
                        "thumbnail": "content/thumbnail/566eb263-1e8d-477b-a455-b7e0f24a0ba2.jpg"
                    }
                ]
            }
            ```
        - **get_all_text_gegments** requires a query parameter named **v** and v contains a video_id that is used to get all text segments of the video

            `http://127.0.0.1:8000/video/watch?v=a5052938-dfa6-4be7-99aa-e66e52d1f328`
            ```json
            {
                "hint": "got_all_segments",
                "code": 1,
                "data": {
                    "segments": [
                        {
                            "clip_id": "332d31cc-bdb5-478f-b9d8-aad41b27a8b4",
                            "text": " No one likes you. You're a top-dead.",
                            "start_time": 0.0,
                            "end_time": 6.0
                        },
                        {
                            "clip_id": "a83dda7e-d54c-49b2-9cb8-a82131dca4a0",
                            "text": " You're a malley. Do you have a car somewhere?",
                            "start_time": 6.0,
                            "end_time": 9.0
                        }
                    ],
                    "thumbnail": "content/thumbnail/a5052938-dfa6-4be7-99aa-e66e52d1f328.jpg",
                    "title": "The Rust Helicopter incident of 2023",
                    "channel": "Stimpee",
                    "duration": 859,
                    "source_url": "https://youtube.com/watch?v=WQsQFIWIveA",
                    "channel_id": "UC2MjZanWOfyfsrHOyitmXbQ"
                }
            }
        - **get_video_clip** accepts clip_id as json data and generate the clip from the video and returns the clip url
            ```json
            {
                "clip_id": "32d31cc-bdb5-478f-b9d8-aad41b27a8b4"
            }
            ```
    - Tasks
        - **task_get_youtube_video_info** accepts video_url and validate the url using pytube library and get video_info
        - **task_process_and_save_requested_video_info_in_db** takes user_id, paltform, video_url as input and save requested video_info in **RequestedVideo** table
        - **task_get_requested_video_data** takes user_id as input and get requested queue data from **RequestedVideo**  table
        - **start_downaloding_youtube_video** takes video url, user id, video id as input start downloading youtube video using **pytube** library
        - **convert_video_to_audio** takes user_id, file_name as input and convert the video into audio for future processing
        - **convert_video_to_text** takes user_id, video_id, file_name as input and generate the text segemnst from audio using **whisper** model.
        - **task_download_youtube_video** is a shred task under celery that is used for background processing of the video to text segments
        - **task_get_process_session_info** takes user_id as input and search its latest process session and if its not completed then it sends the process info in response
        - **task_get_process_video_completed_info** takes user_id as input and gets all the video data from database which are flagged as processed and match with the processed by user
        - **task_get_all_processed_videos** takes a argument that is optional and if no argument passed then it returns all videos which ar amrked as processed but if a argument is passed and valid then it checks in database and filter all the video title and and video processed flag and then returns all the video data
        - **task_get_all_text_segments_of_video** takes video_id as input and returns all the text_segments of that video
        - **task_get_video_clip_stream** takes clip_id as stream and it generate the clip from the full video if the video doesnt have the specific clip already else it skips the clip generation

- Config
    - Views
        - **serve_thumbnail** accepts file_name as endpoint path and if it finds the file in the path **content/thumbnail/** then it returns the thumbnail file
        - **serve_video_segment** accepts file_name as endpoint path and if it finds the file_name in that folder **content/segment/** then it returns the file in response
## Screenshots
Docker Running On Terminal
![App Screenshot](https://raw.githubusercontent.com/DeepProgram/Video2TextAPI/screenshot/terminal.png)

Database List In Admin Panel
![App Screenshot](https://raw.githubusercontent.com/DeepProgram/Video2TextAPI/screenshot/admin_panel.png)

Content Folder Tree
![App Screenshot](https://raw.githubusercontent.com/DeepProgram/Video2TextAPI/screenshot/content_tree.png)
