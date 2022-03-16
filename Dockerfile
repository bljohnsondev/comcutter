FROM lsiobase/alpine:3.11

WORKDIR /tmp

RUN apk --no-cache add python3 py3-pip ffmpeg tzdata bash curl \
&& apk --no-cache add --virtual=builddeps autoconf automake libtool git ffmpeg-dev wget tar build-base \
&& ln -s /usr/bin/python3 /usr/bin/python \
&& pip3 install flask waitress pyyaml \
&& wget http://prdownloads.sourceforge.net/argtable/argtable2-13.tar.gz \
&& tar xzf argtable2-13.tar.gz \
&& cd argtable2-13/ && ./configure && make && make install \
&& cd /tmp && wget https://github.com/erikkaashoek/Comskip/archive/refs/tags/0.82.009.tar.gz -O /tmp/comskip-0.82.009.tar.gz \
&& tar xfz ./comskip-0.82.009.tar.gz \
&& cd Comskip-0.82.009 && ./autogen.sh && ./configure && make && make install \
&& cd /tmp && git clone https://github.com/BrettSheleski/comchap.git \
&& cd comchap && make && make install \
&& apk del builddeps \
&& rm -rf /var/cache/apk/* /tmp/* /tmp/.[!.]*

COPY ./src /comlistener/

WORKDIR /

COPY root/ /

