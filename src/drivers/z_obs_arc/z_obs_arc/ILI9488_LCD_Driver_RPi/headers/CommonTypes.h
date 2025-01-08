#pragma once

struct Position{
    int x;
    int y;
};
struct Size{
    unsigned int width;
    unsigned int height;
};

enum Click{
    ONE_CLICK,
    DOUBLE_CLICK,
    RELEASE,
    NONE
};
