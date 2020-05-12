rm -fr /usr/local/lib/python3.*/site-packages/lollypop/
ninja -C build install
reset
lollypop -e
