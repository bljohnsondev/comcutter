# Comcutter
This is a basic container that wraps the [Comskip](https://github.com/erikkaashoek/Comskip) and [Comchap](https://github.com/BrettSheleski/comchap) utilities.  It utilizes a REST api endpoint to accept filenames for the commercial skipping process.  I'm using it with the following workflow:

1. OTA shows get recorded by [Jellyin](https://jellyfin.org/) and saved into a *DVR* directory on an NFS share
2. A Jellyfin post processing script uses *curl* to make a call to this API endpoint
3. After receiving the API call it uses the Comskip utility to remove commercials
4. Once the commercial skipping process is complete another post processing script can be called

Doing it this way allows me to let an external container separate from Jellyfin handle the commerical skipping procedure.  This can be run on a separate machine as long as there is a volume mount from this container to the NFS share.

## Config file
The config file is a YAML file and looks something like this:

```yaml
api:
  apikey: "YOUR_GENERATED_API_KEY"
  log_dir: "/data/logs"
  log_level: "debug"
  library_dir: "/library"
  port: 8080

comskip:
  comskip_cmd: "/usr/local/bin/comskip"
  comskip_ini: "/data/config/comskip.ini"
  cmd: "/usr/local/bin/comcut"
  keep_edl: true
  timeout: 300
  size_percentage: 0.7

postprocess:
  cmd: "/data/scripts/postcall.sh"
```

The configuration above should be fairly self explanatory.  Some less obvious configurations are:
* **apikey** - This is your own generated apikey.  You can assign whatever you want here but it just provides some basic protection for your API endpoint.  It is required.
* **log_dir** - This is the directory where the *comcutter.log* file resides.  If you would rather log to console then omit this.
* **library_dir** - This is the directory where the media is located.  This is usually the mounted volume to your media.
* **cmd** - This is the command that is run to process the video file.  This should be either */usr/local/bin/comcut* or */usr/local/bin/comchap*.
* **timeout** - This is the timeout period in seconds for the processing command.  By default I have it set to 5 minutes.  If the process takes longer than this it will be aborted and an error thrown in the log files.
* **size_percentage** - This is just to ensure that you didn't start out with a 2 GB video file and after cutting commercials it ended up being 250K.  This is a sign of a problem during the commercial skipping process.  This is the threshold of the percentage of the original file size.  The default value is 0.7 which means that the final version of the file should be at least 70% as large as the original.
* **postprocess / cmd** - This is a command that is run after the process has been completed successfully.  This is a placeholder I put in for future use.  I may end up doing some more fun stuff with this like kicking off a [Node RED](https://nodered.org/) workflow to perform further actions like sending [Gotify](https://gotify.net/) notifications.

### Additional advanced parameters

* **host** - This is the IP address that the server will listen on.  By default it listens on all addresses with `0.0.0.0`.
* **uri** - This is the *URI* that the API route uses.  By default the URI is `/comskip`.

If you were to change *host* to localhost `127.0.0.1` , *port* to `9000` and *uri* to `/comcutter` then the server will listen on `127.0.0.1:9000/comcutter`.

## Docker compose example
Here is a basic example of a *docker-compose.yml* file for using this image.

**NOTE** - this image is based on the [LinuxServer.io](https://www.linuxserver.io/) base image.  That's why you will see the standard LSIO logo on startup.

```yaml
version: "2.1"
services:
  comcutter:
    image: bljohnsondev/comcutter
    container_name: comcutter
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Chicago
    ports:
      - 8080:8080
    volumes:
      - /your/path/to/data:/data
      - /your/path/to/media/library:/library
    restart: unless-stopped
```

### Volume mounts
* **data** - This is the main data directory.  It contains two directories that will be initialized on startup.
	* **config** - This is where the *comskip.ini* and *config.yml* files reside
	* **logging** - This is where the *comcutter.log* file resides
* **library** - This is the directory where your media is stored.

## Example script to call API

This example bash script uses *curl* to kick off a commercial skip operation.  I am using a similar script for post processing with Jellyfin.  Jellyfin calls this and passes the full file path to the recording as the command argument.

Note that the file path will be specific to the Jellyfin container.  If the Jellyfin library mount (for example `/library`) differs from the Comcutter library mount (for example `/data/library`) you will need to use `sed` or some other utility to strip this from the path.

```bash
#!/bin/bash

filepath="$@"

curl -X POST \
  http://localhost:8080/comskip \
  -H 'Content-Type: application/json' \
  -d "{\"api\": \"YOUR_GENERATED_API_KEY\", \"file\": \"${filepath}\"}"
```

## Other things

* The API server uses a queue.  Calling it should give you an immediate JSON response saying that the file is being processed.  This **does not** mean that the process is complete.  This only means that the file has been accepted and added to the queue.  Due to the fact that the commercial skipping process could take a significant amount of time the API server does not block the request until complete.
* Can you run this without Docker?  Absolutely.  Clone the repo and just use the Python code in the *src* directory.  Copy the default *config.yml* file in the `/root/defaults` directory in the same folder with the Python code and modify it to fit your needs.  By default it looks in the current directory for the config file.  Run the `comlistener.py` file to start up the API server.

## Links

* [Github](https://github.com/bljohnsondev/comcutter)
* [Docker Hub](https://hub.docker.com/r/bljohnsondev/comcutter)
