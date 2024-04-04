LISTENERS = {}
var allow_submit = true;

console = { log: function(x) { call_python("log", x); } }
document = { 
    querySelectorAll: function(s) { var handles = call_python("querySelectorAll", s);
            return handles.map(function(h) { return new Node(h) }); },
    createElement: function(tagName) { return new Node(call_python("createElement", tagName));}}
function Node(handle) { this.handle = handle}
Node.prototype.getAttribute = function(attr) { return call_python("getAttribute", this.handle, attr); }
Node.prototype.addEventListener = function(type, listener) {
    if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
    var dict = LISTENERS[this.handle];
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(listener);
}

function lengthCheck() {
    var name = this.getAttribute("name");
    var value = this.getAttribute("value");
    allow_submit = value.length <= 100;
    if (!allow_submit){
        console.log("Input " + name + " has too much text.")
    }
}
Node.prototype.dispatchEvent = function(evt) {
    var type = evt.type
    var handle = this.handle;
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(this, evt);
    }
    return evt.do_default;
}
Node.prototype.appendChild = function(child) {
    call_python("appendChild", this.handle, child.handle);
}
Node.prototype.insertBefore = function(child, sibling) {
    if(sibling) {
        call_python("insertBefore", this.handle, child.handle, sibling.handle);
    }
    else {
        call_python("insertBefore", this.handle, child.handle);     
    }
}
Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML_set", this.handle, s.toString());
    }
});
Object.defineProperty(Node.prototype, 'children', {
    get: function() {
        var handles = call_python("getChildren", this.handle)
        return handles.map(function(h) { return new Node(h) });
    }
});
Object.defineProperty(document, "cookie", {
    get: function () {
        return call_python("get_cookies")
    },
    set: function (c) {
        call_python("set_cookies", c.toString())
    }
});
function Event(type) {
    this.type = type
    this.do_default = true;
}

Event.prototype.preventDefault = function() {
    this.do_default = false;
}

function XMLHttpRequest() {}

XMLHttpRequest.prototype.open = function(method, url, is_async) {
    if (is_async) throw Error("Asynchronous XHR is not supported");
    this.method = method;
    this.url = url;
}

XMLHttpRequest.prototype.send = function(body) {
    this.responseText = call_python("XMLHttpRequest_send",
        this.method, this.url, body);
}