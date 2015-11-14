"use strict";

function changeCursor(prop) {
    prop = prop || "default";
    $("body").css("cursor", prop);
}

function cacheBuster(str) {
    return str + "?" + (new Date()).getTime();
}

$.fn.setSrc = function (src, callback) {
    var $node = this;
    $node.attr("src", src);
    if (callback) {
        $node.each(function () {
            var $each = $(this);
            var complete = this.complete;
            function handler() {
                if (!complete)
                    $each.off("load", null, handler);
                callback.call($each[0]);
            }
            if (!complete) {
                $each.on("load", handler);
            } else {
                handler();
            }
        });
    }
    return this;
};

$.fn.detectMouse = function (opt) {
    var move = opt.move,
        scratch = opt.scratch,
        hover = opt.hover,
        down = opt.down,
        up = opt.up;

    this.each(function () {
        var dom = this;
        var pressingButton = false;
        var $node = $(dom);
        var getPos = function (ev) {
            var offset = $node.offset();
            return {
                x: ev.pageX - offset.left,
                y: ev.pageY - offset.top
            };
        };
        $node
            .mousedown(function (ev) {
                pressingButton = true;
                if (down)
                    down.call(dom, getPos(ev));
            })
            .mousemove(function (ev) {
                if (!pressingButton && hover)
                    hover.call(dom, getPos(ev));
                if (pressingButton && scratch)
                    scratch.call(dom, getPos(ev));
                if (move)
                    move.call(dom, getPos(ev), pressingButton);
            });
        $("body").mouseup(function (ev) {
            pressingButton = false;
            if (up)
                up.call(this, getPos(ev));
        });
    });
    return this;
};

var SimpleStateRenderer = (function () {
    var baseHelper = {
        $: window.jQuery,
        root: "body",
        clearRoot: false,
        setState: function (state) {
            this.state = state;
        },
        ready: function (jQuery) {
            if (!!jQuery) {
                this.$ = jQuery;
            }

            this._readyComplete = false;
            var $root = this.$(this.root);
            this.$root = $root;
            this.didReady($root);
            this._readyComplete = true;
            this.invalidate();
            return this;
        },
        didReady: function () {},
        didRenderAll: function () {},
        invalidate: function () {
            if (!this._readyComplete) {
                return;
            }

            var $node = this.$(this.root);
            if (this.clearRoot) {
                $node.empty();
            }
            this.renderAll($node, this.state);
        },
        renderAll: function ($root, state) {
        }
    };

    return function (obj) {
        var result = {};

        var upper = {};
        for (var key in baseHelper) {
            if (typeof baseHelper[key] === 'function') {
                upper[key] = (function () {
                    var fn = baseHelper[key];
                    return function () {
                        return fn.apply(result, arguments);
                    };
                })();
            } else {
                upper[key] = baseHelper[key];
            }
        }

        result['orig'] = upper;
        result['state'] = {};

        for (var key in baseHelper) {
            result[key] = baseHelper[key];
        }
        for (var key in obj) {
            result[key] = obj[key];
        }
        return result;
    };
})();

var CropperRenderer = function (root, _warp_id) {
    return SimpleStateRenderer({
        root: root,
        clearRoot: false,
        ctx: null,
        DETECT_LENGTH: 25,
        state: {
            warp_id: _warp_id,
            width: 0,
            height: 0,
            left: 0,
            right: 0,
            loading: true,
            initial: true
        },
        renderAll: function ($root, state) {
            var ctx = this.ctx;
            var img = this.$img[0];
            if (!state.initial && !state.loading) {
                ctx.drawImage(img, 0, 0);
                ctx.beginPath();
                $([state.left, state.right]).each(function () {
                    ctx.moveTo(this, 0);
                    ctx.lineTo(this, state.height);
                });

                $([state.top, state.bottom]).each(function () {
                    ctx.moveTo(0, this);
                    ctx.lineTo(state.width, this);
                });

                ctx.lineWidth = 2;
                ctx.strokeStyle = "#ff0000";
                ctx.stroke();
            }
        },
        didReady: function ($root) {
            var this_ = this;
            var $canvas = $("<canvas class='warp-canvas'>");
            var $img = $("<img class='warp-iamge' style='display: none'>");
            $root.append($img, $canvas);

            this.ctx = $canvas[0].getContext("2d");
            this.$canvas = $canvas;
            this.$img = $img;

            this.resync();

            var lineCtrl = null;
            this.$canvas.detectMouse({
                down: function (pos) {
                    lineCtrl = this_.nearestLine(pos);
                    if (lineCtrl != null) {
                        changeCursor("pointer");
                    }
                },
                scratch: function (pos) {
                    if (lineCtrl == null)
                        return;
                    var val = lineCtrl.extract(pos);
                    console.log(val);
                    console.log("LEFT : " + this_.state.left);
                    lineCtrl.attr(val);
                    this_.invalidate();
                },
                hover: function (pos) {
                    var line = this_.nearestLine(pos);
                    if (line != null) {
                        changeCursor("pointer");
                    } else {
                        changeCursor();
                    }
                },
                up: function () {
                    lineCtrl = null;
                    changeCursor();
                }
            });
        },
        nearestLine: function (pos) {
            var this_ = this;
            var state = this.state;
            var LIMIT = this.DETECT_LENGTH;
            var left = parseInt(state.left),
                right = parseInt(state.right),
                top = parseInt(state.top),
                bottom = parseInt(state.bottom);
            var hMid = Math.ceil((left + right) / 2),
                vMid = Math.ceil((top + bottom) / 2);

            var attrName;
            var gap = null;
            if (left - LIMIT <= pos.x && pos.x <= Math.min(hMid, left + LIMIT)) {
                attrName = 'left';
                gap = Math.abs(pos.x - left);
            } else if (Math.max(hMid, right - LIMIT) <= pos.x && pos.x <= right + LIMIT) {
                attrName = 'right';
                gap = Math.abs(pos.x - right);
            }
            if (top - LIMIT <= pos.y && pos.y <= Math.min(vMid, top + LIMIT)) {
                if (!gap || gap > Math.abs(pos.y - top))
                    attrName = 'top';
            } else if (Math.max(vMid, bottom - LIMIT) <= pos.y && pos.y <= bottom + LIMIT) {
                if (!gap || gap > Math.abs(pos.y - bottom))
                    attrName = 'bottom';
            }

            if (!attrName)
                return;

            var counterAttrName;
            var isTL = attrName === 'left' || attrName === 'top';
            var isHorizontal = attrName === 'left' || attrName === 'right';

            if (attrName === 'left') {
                counterAttrName = 'right';
            } else if  (attrName === 'right') {
                counterAttrName = 'left';
            } else if (attrName === 'top') {
                counterAttrName = 'bottom';
            } else if (attrName === 'bottom') {
                counterAttrName = 'top';
            }
            console.log("DIR " + attrName + "  COUNTER " + counterAttrName);

            return {
                extract: function (pos) {
                    if (isHorizontal) {
                        return pos.x;
                    } else {
                        return pos.y;
                    }
                },
                attr: function (val) {
                    var state = this_.state;
                    if (val === undefined) {
                        return state[attrName];
                    } else {
                        var counterVal = parseInt(state[counterAttrName]);
                        var limiter = isTL? Math.min : Math.max;
                        state[attrName] = limiter(parseInt(val), counterVal);
                        return this;
                    }
                }
            };
        },
        onLoadImage: function () {
            var state = this.state;
            var width = this.$img[0].naturalWidth,
                height = this.$img[0].naturalHeight;

            state.loading = false;
            state.width = width;
            state.height = height;
            this.$canvas.css("width", width);
            this.$canvas.css("height", height);
            this.$canvas[0].width = width;
            this.$canvas[0].height = height;
            if (state.initial) {
                state.left = 0;
                state.top = 0;
                state.right = width - 1;
                state.bottom = height - 1;
                state.initial = false;

                console.log(state);
            }
            this.invalidate();
        },
        resync: function (warp_id) {
            if (warp_id == null) {
                warp_id = this.state.warp_id;
            } else {
                this.state.warp_id = warp_id;
            }
            var this_ = this;

            this.state.loading = true;
            this.$img.setSrc(cacheBuster("/warp/image/" + warp_id), function () {
                this_.onLoadImage();
            });
        },
        getRectData: function () {
            var state = this.state;
            if (!state.loading) {
                return {
                    crop: {
                        left: state.left,
                        right: state.right,
                        top: state.top,
                        bottom: state.bottom
                    }
                };
            } else {
                return {};
            }
        }
    });
};

var WarpRenderer = function (root, _warp_id, rectCtrl) {
    return SimpleStateRenderer({
        root: root,
        clearRoot: false,
        state: {
            warp_id: _warp_id
        },
        cropperRenderer: null,
        getWarpId: function () {
            return this.state.warp_id;
        },
        renderAll: function ($root, state) {
            var warp_id = state.warp_id,
                threshold = state.threshold; 
            $root.attr("data-warp-id", state.warp_id);
        },
        _fillLi: function ($li) {
            var state = this.state;
            var $cropper = $("<div class='cropper'>");
            this.$cropper = $cropper;
            $li
            .append(
                $cropper,
                $("<h2 class='lang-heading'>Src text(Jpn)</h2>"),
                $("<div class='src-lang'>"),
                $("<h2 class='lang-heading'>Translated text(Kor)</h2>"),
                $("<div class='dest-lang'>"),
                $("<form class='opt-form'>").append(
                    $("<fieldset>").append(
                        $("<label>Method</label>"),
                        $("<div class='radio-group'>").append(
                            $("<input type='radio' name='threshold_type' value='otsu' checked>"),
                            "otsu"
                        ),
                        $("<div class='radio-group'>").append(
                            $("<input type='radio' name='threshold_type' value='naive'>"),
                            "naive"
                        ),
                        $("<div class='radio-group'>").append(
                            $("<input type='radio' name='threshold_type' value='adaptive'>"),
                            "adaptive"
                        ),
                        $("<div class='input-group'>").append(
                            $("<label>threshold: </label>"),
                            $("<input type='text' class='opt' name='naive_value' value='80'>"),
                            $("<label>C: </label>"),
                            $("<input type='text' class='opt' name='adaptive_C' value='3'>"),
                            $("<label>Block size: </label>"),
                            $("<input type='text' class='opt' name='adaptive_block_size' value='5'>")
                        )
                    ),
                    $("<div class='input-group'>").append(
                        $("<label>Rotation</label>"),
                        $("<input type='text' name='rotation' value='0.0'>")
                    ),
                    $("<input type='submit' value='Update'>")
                ),
                $("<button class='btn-warp-ocr'>OCR</button>")
            );
            this.cropperRenderer = CropperRenderer($cropper, state.warp_id).ready();
        },
        didReady: function ($root) {
            var this_ = this;
            this._fillLi($root);
            $root.find(".btn-warp-ocr").click(function () {
                this_.ocr();
            });
            var $form = $root.find(".opt-form");
            $form.submit(function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                this_.updateWarpId();
            });
            this_._showOpt();
            $form.find("[name=threshold_type]").change(function () {
                this_._showOpt();
            });
        },
        _showOpt: function () {
            var $form = this.$root.find(".opt-form");
            var method = $form.find("[name=threshold_type]:checked").val();
            $form.find(".opt").hide();
            if (method === 'naive') {
                $form.find("[name='naive_value']").show();
            } else if (method === 'adaptive') {
                $form.find("[name='adaptive_C'],[name='adaptive_block_size']").show();
            }
        },
        updateWarpId: function (callback) {
            var this_ = this;
            var $form = $(this.root).find(".opt-form");
            var rect = rectCtrl.get(this.state.warp_id);

            var getField = function (name) {
                return $form.find("[name='" + name + "']");
            };

            $.ajax({
                url: "/warp/" + this.state.warp_id,
                method: "DELETE"
            });
            console.log("ASD>> ");
            console.log(rect);
            rect.warp_id = null;
            $.ajax({
                url: "/warp",
                method: 'POST',
                data: JSON.stringify({
                    rect: rect.points,
                    rotation: parseFloat(getField("rotation").val()),
                    threshold: (function () {
                        var method = $form.find("[name=threshold_type]:checked").val();
                        var value = null;
                        if (method === 'adaptive') {
                            value = {
                                C: parseInt(getField("adaptive_block_size").val()),
                                block_size: parseInt(getField("adaptive_C").val())
                            };
                        } else if (method === 'naive') {
                            value = parseInt(getField("naive_value").val());
                        }
                        return {
                            method: method,
                            value: value
                        };
                    })()
                }),
                contentType: "application/json",
                success: function (data) {
                    var warp_id = data.warp_id;
                    rect.warp_id = warp_id;
                    this_.resync(warp_id);
                    if (callback)
                        callback(warp_id);
                }
            });
        },
        resync: function (warp_id) {
            this.state.warp_id = warp_id;
            this.cropperRenderer.resync(this.state.warp_id);
        },
        ocr: function () {
            var warp_id = this.getWarpId();
            var $srcLang = this.$root.find(".src-lang"),
                $destLang = this.$root.find(".dest-lang");

            $srcLang.addClass("loading");
            $destLang.addClass("loading");
            $srcLang.html("Wait...");
            $destLang.html("Wait...");
            $.ajax({
                url: "/ocr/" + warp_id,
                data: JSON.stringify(this.cropperRenderer.getRectData()),
                contentType: "application/json",
                method: 'POST',
                success: function (data) {
                    $srcLang.empty();
                    $destLang.empty();
                    $(data.content.split("\n")).each(function () {
                        $("<div>").text(this).appendTo($srcLang);
                    });
                    $(data.translated.split("\n")).each(function () {
                        $("<div>").text(this).appendTo($destLang);
                    });
                },
                error: function () {
                    $srcLang.html("Network Error");
                    $destLang.html("Network Error");
                },
                complete: function () {
                    $srcLang.removeClass("loading");
                    $destLang.removeClass("loading");
                }
            });
        },
        remove: function () {
            var warp_id = this.state.warp_id;
            $root.remove();
            $.ajax({
                url: "/warp/" + warp_id,
                method: "DELETE"
            });
            rectCtrl.remove(warp_id);
        }
    });
};

var cannyRenderer = SimpleStateRenderer({
    root: ".canny-wrapper",
    clearRoot: false,
    dumpToForm: function (data) {
        var state = this.state;
        var $form = this.$root.find(".opt-form");
        $form.find("[name=canny-level]").val(data.canny_level);
        $form.find("[name=kernel-size]").val(data.kernel_size);
        $form.find("[name=blur-size]").val(data.blur_size);
    },
    _next_ti: null,
    loadSrc: function () {
        var this_ = this;
        var $img = this.$root.find(".mn-canny-image");
        clearInterval(this._next_ti);
        this._next_ti = null;
        $img.setSrc(cacheBuster("/mn_canny.jpg"), function () {
            this_._next_ti = setTimeout(function () {
                this_.loadSrc();
            }, 2000);
        });
    },
    didReady: function ($root) {
        var this_ = this;
        $.ajax({
            url: "/canny",
            method: "GET",
            success: function (data) {
                this_.dumpToForm(data);
            },
            complete: function () {
                this_.invalidate();
            }
        });
        this.loadSrc();

        var $form = $root.find(".opt-form");
        $form.submit(function (ev) {
            ev.preventDefault();
            ev.stopPropagation();

            $.ajax({
                url: "/canny",
                method: "POST",
                data: JSON.stringify({
                    canny_level: parseInt($form.find("[name='canny-level']").val()),
                    kernel_size: parseInt($form.find("[name='kernel-size']").val()),
                    blur_size: parseInt($form.find("[name='blur-size']").val())
                }),
                contentType: "application/json",
                success: function (data) {
                    this_.dumpToForm(data);
                },
                complete: function () {
                    this_.invalidate();
                    this_.loadSrc();
                }
            });
        });
    }
});

var CanvasRenderer = function (root, getRects, addRect, nearest) {
    var floodFillTool = {
        begin: function (renderer) {
            this.renderer = renderer;
        },
        down: function (pos) {
            var this_ = this;
            changeCursor("waiting");
            $.ajax({
                url: "/floodfill",
                method: 'POST',
                data: JSON.stringify({
                    point: [pos.x, pos.y]
                }),
                contentType: "application/json",
                complete: function () {
                    changeCursor();
                },
                success: function (data) {
                    $(data.rects).each(function () {
                        var rect = {
                            warp_id: null,
                            points: this
                        };
                        addRect(rect);
                    });
                    this_.renderer.invalidate();
                }
            });
        },
        end: function () {}
    };

    
    var dropTool = {
        begin: function (renderer) {
            this.renderer = renderer;
        },
        down: function (pos) {
            var top = Math.max(pos.x - 20, 0);
            var left = Math.max(pos.y - 20, 0);
            var bottom = top + 40,
                right = left + 40;
            addRect({
                points: [
                    [top, left],
                    [top, right],
                    [bottom, right],
                    [bottom, left]
                ],
                warp_id: null
            });
            this.renderer.invalidate();
        },
        end: function () {
        }
    };

    var moveTool = {
        begin: function (renderer) {
            this.renderer = renderer;
        },
        pointProxy: null,
        down: function (pos) {
            var pointProxy = nearest(pos);
            if (pointProxy != null) {
                this.pointProxy = pointProxy;
                changeCursor("pointer");
            }
        },
        up: function () {
            this.pointProxy = null;
            changeCursor();
        },
        hover: function (pos) {
            var pointProxy = nearest(pos);
            if (pointProxy != null) {
                changeCursor("pointer");
            } else {
                changeCursor();
            }
        },
        scratch: function (pos) {
            if (this.pointProxy) {
                this.pointProxy.attr(pos);
                this.renderer.invalidate();
            }
        },
        end: function () {
        }
    };

    var toolDict = {
        floodfill: floodFillTool,
        drop: dropTool,
        move: moveTool
    };

    return SimpleStateRenderer({
        root: root,
        state: {
            toolName: null
        },
        clearRoot: false,
        ctx: null,
        $image: null,
        $canvas: null,
        didReady: function ($root) {
            var this_ = this;
            this.$image = $root.find(".mn-image");
            this.$canvas = $root.find(".rect-canvas");
            this.ctx = this.$canvas[0].getContext("2d");

            this.changeTool("floodfill");
            $root.find(".tool-selector > li").click(function () {
                $root.find(".tool-selector > li").removeClass("active");
                $(this).addClass("active");
                this_.changeTool($(this).attr("data-tool"));
            });
            var getHandler = function (handlerName) {
                return function () {
                    var obj = toolDict[this_.state.toolName];
                    if (obj[handlerName]) {
                        obj[handlerName].apply(obj, arguments);
                    }
                };
            };
            var args = {};
            $(["move", "scratch", "hover", "down", "up"]).each(function () {
                args[this] = getHandler(this);
            });
            this.$canvas.detectMouse(args);

            function iter() {
                this_.$image.setSrc(cacheBuster("/mn.jpg"), function () {
                    this_.invalidate();
                    setTimeout(iter, 1000);
                });
            }
            iter();
        },
        changeTool: function (newtool) {
            var obj = toolDict[this.state.toolName];
            if (this.state.toolName)
                obj.end(this);
            this.state.toolName = newtool;
            obj = toolDict[this.state.toolName];
            obj.begin(this);
        },
        renderAll: function ($root) {
            var this_ = this;
            var ctx = this_.ctx;
            ctx.drawImage(this.$image[0], 0, 0);
            $(getRects()).each(function() {
                var rect = this;
                ctx.beginPath();
                for (var idx = 0; idx < 4; idx++) {
                    var bg = rect.points[idx],  // pt list
                        ed = rect.points[(idx + 1) % rect.points.length];
                    ctx.moveTo(bg[0], bg[1]);
                    ctx.lineTo(ed[0], ed[1]);
                }
                ctx.strokeStyle = "#00ff00";
                ctx.lineWidth = 3;
                // ctx.lineCap = "round";
                ctx.stroke();
            });
        }
    });
};

var mainRenderer = SimpleStateRenderer({
    root: ".rect-canvas-wrapper",
    clearRoot: false,
    subrenderers: {},
    canvasRenderer: null,
    state: {
        rects: [] // {points: int array array, warp_id: null or string} array
    },
    didReady: function ($root) {
        var this_ = this;
        this.canvasRenderer = CanvasRenderer($root.find(".canvas-wrapper"), 
            // getRects
            function () {
                return this_.state.rects;
            },
            // addRect
            function (rect) {
                this_.state.rects.push(rect);
            },
            // nearest
            function () {
                return this_.nearest.apply(this_, arguments);
            }
        ).ready();
        $root.find(".clear-warps").click(function () {
            this_.clearRects();
            this_.canvasRenderer.invalidate();
        });
        $root.find(".build-warps").click(function () {
            this_.buildAll(function () {
                this_.invalidate();
                this_.canvasRenderer.invalidate();
            });
        });
    },
    unlinkRects: function () {
        var $warpList = $(this.root).find(".warp-list");
        $warpList.empty();
        $(this.state.rects).each(function () { this.warp_id = null; });
        for (var key in this.subrenderer) {
            this.subrenderers[key].remove();
        }
        this.subrenderers = {};
    },
    clearRects: function () {
        // This function doesn't invoke invalidate()
        var $warpList = $(this.root).find(".warp-list");
        $warpList.empty();
        var rects = this.state.rects;
        this.state.rects = [];
        for (var key in this.subrenderer) {
            this.subrenderers[key].remove();
        }
        this.subrenderers = {};
    },
    DETECT_RADIUS: 25,
    nearest: function (pos) {
        var LIMIT_2 = this.DETECT_RADIUS * this.DETECT_RADIUS;

        // [rect, idx] or undefined
        var accessor;
        var minNorm = null;
        $(this.state.rects).each(function () {
            var rect = this;
            $(rect.points).each(function (idx) {
                var pt = this;
                var dx = pt[0] - pos.x,
                    dy = pt[1] - pos.y;
                var norm = dx * dx + dy * dy;

                if (norm <= LIMIT_2 && (minNorm == null || minNorm > norm)) {
                    minNorm = norm;
                    accessor = [rect, idx];
                }
            });
        });
        if (!accessor)
            return;

        var rect = accessor[0];
        var index = accessor[1];

        return {
            attr: function (val) {
                if (val === undefined) {
                    var pt = rect.points[index];
                    return {
                        x: pt[0],
                        y: pt[1]
                    };
                }
                rect.points[index] = [parseInt(val.x), parseInt(val.y)];
                return this;
            }
        };
    },
    findByWarpId: function (warp_id) {
        var rects = this.state.rects;
        for (var idx = 0; idx < rects.length; idx++) {
            if (rects[idx].warp_id === warp_id) {
                return rects[idx];
            }
        }
    },
    buildAll: function (complete) {
        var this_ = this;
        var rects = this.state.rects;
        this.unlinkRects();
        this.state.rects = rects;
        var $warpList = this.$root.find(".warp-list");

        function iter(rects, idx) {
            if (idx < rects.length) {
                var rect = rects[idx];
                $.ajax({
                    url: "/warp",
                    data: JSON.stringify({
                        rect: rect.points,
                        rotation: 0,
                        threshold: {method: "otsu"}
                    }),
                    contentType: "application/json",
                    method: "POST",
                    success: function (data) {
                        var warp_id = data.warp_id;
                        var $li = $("<li>");
                        $li.appendTo($warpList);

                        rect.warp_id = warp_id;

                        var subrenderer = WarpRenderer($li, warp_id, {
                            get: function (warp_id) {
                                console.log("RECTS>>");
                                console.log(this_.state.rects);
                                return this_.findByWarpId(warp_id);
                            },
                            remove: function (warp_id) {
                                delete this_.subrenderers[warp_id];
                                this_.state.rects = $(this_.state.rects).filter(function () {
                                    return this.warp_id != warp_id;
                                }).toArray();
                            }
                        });
                        subrenderer.ready();
                        this_.subrenderers[warp_id] = subrenderer;
                    },
                    complete: function () {
                        iter(rects, idx + 1);
                    }
                });
            } else {
                if (complete)
                    complete();
            }
        }
        iter(rects, 0);
    }
});


$(document).ready(function () {
    mainRenderer.ready();
    cannyRenderer.ready();
});
