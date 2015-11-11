var SimpleStateRenderer = (function () {
    var baseHelper = {
        $: window.jQuery,
        root: "body",
        clearRoot: true,
        setState: function (state) {
            this.state = state;
        },
        ready: function (jQuery) {
            if (!!jQuery) {
                this.$ = jQuery;
            }

            this._readyComplete = false;
            var $node = this.$(this.root);
            this.didReady($node);
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
        renderAll: function ($parent, state) {
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

var canvasRenderer = SimpleStateRenderer({
    root: ".rect-canvas-wrapper",
    clearRoot: false,
    DETECT_RADIUS: 15,
    state: {
        rects: [], // {points: int array array, warp_id: null or string, rotation: int, rotation: , threshold: ...} array
        tool: "floodfill" // floodfill, drop, move
    },
    didReady: function ($root) {
        this.$image = $wrapper.find(".mn-image");
        this.$canvas = $wrapper.find(".rect-canvas");
        this.ctx = $canvas[0].getContext("2d");
    },
    fillDefault: function (rect) {
        rect.rotation = 0;
        rect.threshold = {
            method: "otsu"
        };
        return rect;
    },
    renderAll: function ($root, state) {
        var this_ = this;
        var ctx = this_.ctx;
        ctx.drawImage(this.$image[0], 0, 0);

        $(state.rects).each(function() {
            var rect = this; // pt list
            ctx.beginPath();
            for (var idx = 0; idx < 4; idx++) {
                var bg = rect.points[idx],
                    ed = rect.points[(idx + 1) % rect.length];
                ctx.moveTo(bg[0], bg[1]);
                ctx.lineTo(ed[0], ed[1]);
            }
            ctx.lineWidth = 3;
            ctx.lineCap = "round";
            ctx.stroke();
        });
    },
    updateImage: function (onload) {
        var url = "/mn.jpg?" + (new Date()).getTime();
        this.$image.attr("src", url).load(onload);
    },
    clearRects: function () {
        // don't invoke invalidate()
        var this_ = this;
        var rects = this_.state.rects;
        this_.state.rects = [];
        function iter(rects, idx) {
            while (idx < rects.length) {
                var rect = rects[idx]
                if (!rect.warp_id) {
                    idx++;
                    continue
                }
                $.ajax({
                    url: "/warp/" + rect.warp_id,
                    method: "DELETE",
                    complete: function () {
                        iter(rects, idx + 1);
                    }
                });
                break;
            }
        }
        iter(rects, 0);
    },
    // [rect, idx] or undefined
    nearest: function (x, y) {
        var result;
        var minNorm = null;
        $(state.rects).each(function () {
            var rect = this;
            $(rect.points).each(function (idx) {
                var pt = this;
                var norm = pt[0] * pt[0] + pt[1] * pt[1];
                if (minNorm == null || minNorm > norm) {
                    minNorm = norm;
                    result = [rect, idx];
                }
            });
        });
        return result;
    },
    findByWarpId: function (warp_id) {
        return $(this.state.rects).filter(function () {
            return this.warp_id == warp_id;
        })[0];
    },
    sync: function (warp_id, complete) {
        var $warpItem = $(this.root).find(".warp-list[data-warp-id='" + warp_id + "']");
        var $newWarpItem = "TODO";

        $newWarpItem.insertAfter($warpItem);
        $warpItem.remove();
    },
    syncAll: function (complete) {
        var rects = this.state.rects;
        var $warpList = $(this.root).find(".warp-list");
        $warpList.empty();

        function iter(rects, idx) {
            if (idx < rects.length) {
                var rect = rects[idx];
                $.ajax({
                    url: "/warp",
                    data: JSON.stringify({
                        rect: rect.points,
                        rotation: parseFloat(rect.rotation || 0),
                        threshold: rect.threshold
                    }),
                    contentType: "application/json",
                    method: "POST",
                    success: function (data) {
                        var url = data.url,
                            warp_id = data.warp_id;
                        // TODO
                    }
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
    },
});

$(document).ready(function () {
    canvasRenderer.ready();
    $(".btn-warp-sync").click(function () {
    });
});
