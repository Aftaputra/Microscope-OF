// TODO: Remember a position and restore that position
// TODO: Right click to auto-focus, centered on that region

var baseURI = "/api/v1"

// Key IDs
var pgupKeyID = 33;
var pgdnKeyID = 34;

var leftKeyID = 37;
var upKeyID = 38;
var rightKeyID = 39;
var downKeyID = 40;

var enterKeyID = 13;
var escKeyID = 27;

var keysDown = {}; //Array of keys down

var stageVelocity = 50;  
var focusVelocity = 20;

var requestLock = false;

// Microscope client-side callibration
//TODO: Move to serverside microscope property
var fovX =  4100;
var fovY = 3146;

window.onload = function() {
    getStagePositions()
    updateTextBoxes()
}

function updateTextBoxes() {
    document.getElementById('stageVelocityText').value = stageVelocity;
    document.getElementById('stageVelocityInput').value = stageVelocity;
    document.getElementById('focusVelocityText').value = focusVelocity;
    document.getElementById('focusVelocityInput').value = focusVelocity;

    document.getElementById('fovXText').value = fovX;
    document.getElementById('fovYText').value = fovY;
}

function updateStagePositions(response) {
    document.getElementById('x_abs').value = response["x"];
    document.getElementById('y_abs').value = response["y"];
    document.getElementById('z_abs').value = response["z"];
}

function getStagePositions() {
    function updatePositionCallback(response, status) {
    console.log(status, response);
    updateStagePositions(response);
    }
    safeRequest("GET", baseURI+"/position", null, updatePositionCallback)
}

function setStagePositions(x_abs, y_abs, z_abs) {
    // Make a position request
    function absMoveCallback(response, status) {
    if (status == 400) {
        alert("Stage cannot be moved further than the safe range.");
    }
    console.log(status, response);
    updateStagePositions(response);
    }
    safeRequest("POST", baseURI+"/position", { "absolute": true, "x": x_abs, "y": y_abs, "z": z_abs}, absMoveCallback)
}

function moveStagePositions(x_rel, y_rel, z_rel) {
    // Make a position request
    function relMoveCallback(response, status) {
    if (status == 400) {
        alert("Stage cannot be moved further than the safe range.");
    }
    console.log(status, response);
    updateStagePositions(response);
    }
    safeRequest("POST", baseURI+"/position", { "absolute": false, "x": x_rel, "y": y_rel, "z": z_rel}, relMoveCallback)
}

function setStagePositionsFromInput() {
    x_abs = Number(document.getElementById('x_abs').value);
    y_abs = Number(document.getElementById('y_abs').value);
    z_abs = Number(document.getElementById('z_abs').value);
    setStagePositions(x_abs, y_abs, z_abs)
}

// Standard callback for user-controller movement
function keyMoveCallback(response, status) {
    console.log(status, response);
    updateStagePositions(response);
}

// Methods for input events

// Click-to-move
function clickHotspotImage(event) {
    if (document.getElementById("clickPositionCheck").checked == true) {
    xCoordinate = event.offsetX;
    yCoordinate = event.offsetY;
    console.log(xCoordinate, yCoordinate)
    xRelative = (0.5*event.target.offsetWidth - xCoordinate)/event.target.offsetWidth;
    yRelative = (0.5*event.target.offsetHeight - yCoordinate)/event.target.offsetHeight;
    console.log(xRelative, yRelative)
    xSteps = xRelative * fovX;
    ySteps = yRelative * fovY;
    console.log(xSteps, ySteps, 0)
    // Make a position request
    moveStagePositions(xSteps, ySteps, 0)
    }
}

// Scroll-to-focus
window.addEventListener('wheel', function(e) {
    multiplier = 1/100;
    z_delta = e.deltaY * multiplier * focusVelocity;
    if (document.getElementById("scrollFocusCheck").checked == true) {
    console.log(z_delta);
    // Make a position request
    safeRequest("POST", baseURI+"/position", { "absolute": false, "z": z_delta}, keyMoveCallback)
    }
});

// Keyboard to move
addEventListener("keydown", function (e) {
    keysDown[e.keyCode] = true; //Add key to array
    console.log(keysDown)

    // If stage movement keys are pressed
    if ((leftKeyID in keysDown) || (rightKeyID in keysDown) || (upKeyID in keysDown) || (downKeyID in keysDown) || (pgupKeyID in keysDown) || (pgdnKeyID in keysDown)) {
        // Calculate movement array
        x_rel = 0;
        y_rel = 0;
        z_rel = 0;
        if (leftKeyID in keysDown) {
        x_rel = x_rel + stageVelocity;
        }
        if (rightKeyID in keysDown) {
        x_rel = x_rel - stageVelocity;
        }
        if (upKeyID in keysDown) {
        y_rel = y_rel + stageVelocity;
        }
        if (downKeyID in keysDown) {
        y_rel = y_rel - stageVelocity;
        }
        if (pgupKeyID in keysDown) {
        z_rel = z_rel - focusVelocity;
        }
        if (pgdnKeyID in keysDown) {
        z_rel = z_rel + focusVelocity;
        }

        // Make a position request
        moveStagePositions(x_rel, y_rel, z_rel)
    }

}, false);

addEventListener("keyup", function (e) {
    delete keysDown[e.keyCode]; //Remove key from array
}, false);

// Methods for making requests
function safeRequest(method, url, payload, callback) {
    if (requestLock == false) {
        var xhr = new XMLHttpRequest();   // new HttpRequest instance 
        xhr.open(method, url);
        requestLock = true;

        xhr.onload = function (e) {
        if (xhr.readyState === 4) {
            if (xhr.status !== 200) {
            console.error(xhr.statusText);
            } 
            callback(JSON.parse(xhr.responseText), xhr.status);
        }
        requestLock = false;
        };

        if (method == "POST" || method == "PUT") {
        xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
        }

        xhr.send(JSON.stringify(payload));

    }
    else {
        console.log("Cannot start new request while previous requets is pending...")
    }
}
