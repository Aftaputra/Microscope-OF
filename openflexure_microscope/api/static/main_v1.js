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

var clientStageParams = {
    "velocityXY": 50,
    "velocityZ": 20,
    "fov": [0, 0]
}

// TODO: Blank out interface except connect menu onload.
window.onload = function() {
    // Populate with current URL
    document.getElementById('microscopeHostInput').value = window.location.hostname
    setHostFromInput()
}

// Microscope API connection class
class apiConnection {
    constructor(hostName, hostPort, apiVersion="v1") {
        this.hostName = hostName;
        this.hostPort = hostPort;
        this.apiVersion = apiVersion;

        this.baseURI = `http://${hostName}:${hostPort}/api/${apiVersion}`

        this.requestLock = false;

        // Used to access 'this' from innter functions
        const self = this;
    }

    // Identify
    identify(callback) {
        function identifyCallback(response, status) {
            if (status == null) {
                console.log("No server found. Aborting.")
            }
            else {
                callback(response, status)
            }
        }
        this.getConfig(identifyCallback)
    }

    // Get microscope state
    getState(callback) {
        this.safeRequest("GET", this.baseURI+"/state", null, callback, false)
    }
    
    // Get microscope configuration
    getConfig(callback) {
        this.safeRequest("GET", this.baseURI+"/config", null, callback, false)
    }

    // New capture
    newCapture(filename, temporary, use_video_port, bayer, callback, resizeWidth=null, resizeHeight=null) {
        var payload = {
            "filename": filename,
            "temporary": temporary,
            "use_video_port": use_video_port,
            "bayer": bayer
        }
    
        if ((resizeWidth) && (resizeHeight)) {
            payload.size = {
                "width": resizeWidth,
                "height": resizeHeight
            }
        }
    
        console.log(payload);
        this.safeRequest("POST", this.baseURI+"/camera/capture/", payload, callback);
    }

    // Delete a capture
    deleteCapture(capture_id, callback) {
        var r = confirm("Warning! This will delete all copies of this capture from the Raspberry Pi. Click OK to proceed.");
        if (r == true) {
            this.safeRequest("DELETE", this.baseURI+"/camera/capture/"+capture_id+"/", null, callback, false)
        }
    }
    
    // Delete all captures in the session
    deleteAllCaptures(callback) {
        var r = confirm("Warning! This will delete all copies of all captures from the Raspberry Pi. Click OK to proceed.");
        if (r == true) {
            this.safeRequest("DELETE", this.baseURI+"/camera/capture/", null, callback, false)
        }
    }
    
    // Get the list of captures in the session
    getCaptures(callback) {
        this.safeRequest("GET", this.baseURI+"/camera/capture", null, callback, false)
    }

    // Move stage absolute
    setStagePositions(x_abs, y_abs, z_abs, callback, absolute=false) {
        // Make a position request
        this.safeRequest("POST", this.baseURI+"/stage/position", { "absolute": absolute, "x": x_abs, "y": y_abs, "z": z_abs}, callback)
    }

    // Method for making requests
    safeRequest(method, url, payload, callback, lock=true, force=false) {
        var allowRequest;

        if (force == true) {
            allowRequest = true;
        }
        else {
            allowRequest = !(self.requestLock)
        }

        if (allowRequest == true) {
            var xhr = new XMLHttpRequest();   // new HttpRequest instance 
            xhr.open(method, url);
    
            if (lock == true) {  // If request is using the lock
                self.requestLock = true;  // Hold the lock
            }
    
            xhr.onload = function(e) {
                if (xhr.readyState === 4) {
                    if (lock == true) {  // If request is using the lock
                        self.requestLock = false;  // Release the lock
                    }
    
                    if (xhr.status !== 200) {
                        console.error(xhr.statusText);
                    } 
                    callback(JSON.parse(xhr.responseText), xhr.status);
                }
            };

            xhr.onerror = function(e) {
                callback("An error occurred during the transaction.", null);
            }
    
            if (method == "POST" || method == "PUT") {
                xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
            }
    
            xhr.send(JSON.stringify(payload));
    
        }
        else {
            console.log("Cannot start the following request while the previous requets is pending:")
            console.log(method, url, payload)
        }
    }
    
}

// Declare connection
var api = null

// Setup methods
function setHostFromInput() {
    hostName = document.getElementById('microscopeHostInput').value;
    hostPort = document.getElementById('microscopePortInput').value;

    api = new apiConnection(hostName, hostPort)
    api.identify(loadInterfaceFromHost)
}

// Populate the UI from a connected host
function loadInterfaceFromHost(response, status) {
    if (status == 200) {
        // Populate the preview panel
        streamContent = `<img src="${api.baseURI}/stream" ondblclick="clickHotspotImage(event);">`
        document.getElementById("streambox").innerHTML = streamContent;

        // Update UI with client params
        updateClientValues();

        // Update UI with microscope state
        api.getState(updateStateValues)

        // Update UI with microscope config
        api.getConfig(updateConfigValues)

        // Update UI with captures
        api.getCaptures(constructCaptureList)
        
    }
}

function updateClientValues() {
    // Microscope velocity
    document.getElementById('stageVelocityText').value = clientStageParams.velocityXY;
    document.getElementById('stageVelocityInput').value = clientStageParams.velocityXY;
    document.getElementById('focusVelocityText').value = clientStageParams.velocityZ;
    document.getElementById('focusVelocityInput').value = clientStageParams.velocityZ;
}

function updateStateValues(response, status){
    if (status == 200) {
        updatePositionValues(response);
    }
}

function updateConfigValues(response, status){
    if (status == 200) {
        updateFovValues(response);
    }
}

function updatePositionValues(state) {
    document.getElementById('x_abs').value = state.stage.position.x;
    document.getElementById('y_abs').value = state.stage.position.y;
    document.getElementById('z_abs').value = state.stage.position.z;
}

function updateFovValues(config) {
    clientStageParams.fov = config.fov
    console.log(clientStageParams.fov)
}

// Cosmetic methods

// Adds/removes a class to a specified div
function toggleClassToDiv(div_id, class_name) {
    document.getElementById(div_id).classList.toggle(class_name)
}

function updateCaptures() {
    api.getCaptures(constructCaptureList)
}

function deleteAllCaptures() {
    api.deleteAllCaptures(updateCaptures)
}

function constructCaptureList(response) {
    // Clear captures list
    var capturesNode = document.getElementById("captures");

    while (capturesNode.firstChild) {
        capturesNode.removeChild(capturesNode.firstChild);
    }

    // Reverse so newest capture appears first
    response.reverse()

    // For each capture in the response array
    response.forEach(function(element) {
        // Store the capture object URI
        element_uri = `${api.baseURI}/camera/capture/${element.metadata.id}`

        // Generate inner HTML from capture object
        html = `
        <div class="capture-thumb"><img src="${element_uri}/download?thumbnail=true"></div>
        <div class="capture-actions"> 
            <div class='capture-heading'>${element.metadata.filename}</div>
            <br>
            <button type="button" class="capture-button" onclick="window.open('${element_uri}/download');">Image</button>
            <button type="button" class="capture-button" onclick="window.open('${element_uri}/metadata');">Metadata</button>
            <br>
            <button type="button" class="capture-button" onclick="window.open('${element_uri}/', '_blank');">JSON</button>
            <button type="button" class="capture-button" onclick="api.deleteCapture('${element.metadata.id}', constructCaptureList);">Delete</button>
            <br>
        </div>
        `

        // Create a new capture div, and append HTML
        var div = document.createElement("div");
        div.className = "capture";
        div.innerHTML = html;
        capturesNode.appendChild(div);
    });

}

function newCaptureFromInput() {
    captureFilenameInput = document.getElementById('captureFilenameInput');
    captureTemporaryCheck = document.getElementById('captureTemporaryCheck');
    captureFullResolutionCheck = document.getElementById('captureFullResolutionCheck');
    captureBayerCheck = document.getElementById('captureBayerCheck')

    captureResizeCheck = document.getElementById('captureResizeCheck');
    captureWidthInput = document.getElementById('captureWidthInput')
    captureHeightInput = document.getElementById('captureHeightInput')

    // Get filename if one is given
    if (captureFilenameInput.value === "") {
        filename = null;
    }
    else {
        filename = captureFilenameInput.value;
    }

    if (captureResizeCheck.checked) {
        resizeWidth = Number(captureWidthInput.value);
        resizeHeight = Number(captureHeightInput.value);
    }
    else {
        resizeWidth = null;
        resizeHeight = null;
    }

    // Make a capture request
    api.newCapture(
        filename, 
        captureTemporaryCheck.checked, 
        !(captureFullResolutionCheck.checked), 
        captureBayerCheck.checked, 
        updateCaptures,
        resizeWidth=resizeWidth, 
        resizeHeight=resizeHeight
    );

}

function newCaptureResizeToggle(checkbox) {
    captureWidthInput = document.getElementById('captureWidthInput')
    captureHeightInput = document.getElementById('captureHeightInput')

    captureWidthInput.disabled = !(checkbox.checked)
    captureHeightInput.disabled = !(checkbox.checked)
}

// Move stage methods

function setStagePositionsFromInput() {
    x_abs = Number(document.getElementById('x_abs').value);
    y_abs = Number(document.getElementById('y_abs').value);
    z_abs = Number(document.getElementById('z_abs').value);

    // Make a position request
    api.setStagePositions(x_abs, y_abs, z_abs, updatePositionValues, absolute=true)
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
        xSteps = xRelative * clientStageParams.fov[0];
        ySteps = yRelative * clientStageParams.fov[1];
        console.log(xSteps, ySteps, 0)

        // Make a position request
        api.setStagePositions(xSteps, ySteps, 0, updatePositionValues)
    }
}

// Scroll-to-focus
window.addEventListener('wheel', function(e) {
    multiplier = 1/100;
    z_delta = e.deltaY * multiplier * clientStageParams.velocityZ;
    if ((document.getElementById("scrollFocusCheck").checked == true) && (e.target.parentNode.classList.value == "scrolltarget")) {
        console.log(z_delta);
        console.log(e.target.parentNode.classList.value);

        // Make a position request
        api.setStagePositions(0, 0, z_delta, updatePositionValues)
    }
});

// Keyboard to move
addEventListener("keydown", function (e) {
    keysDown[e.keyCode] = true; //Add key to array

    // If not currently in an input box
    if (!(e.target instanceof HTMLInputElement)) {
        // If stage movement keys are pressed
        if ((leftKeyID in keysDown) || (rightKeyID in keysDown) || (upKeyID in keysDown) || (downKeyID in keysDown) || (pgupKeyID in keysDown) || (pgdnKeyID in keysDown)) {
            // Calculate movement array
            x_rel = 0;
            y_rel = 0;
            z_rel = 0;
            if (leftKeyID in keysDown) {
                x_rel = x_rel + clientStageParams.velocityXY;
            }
            if (rightKeyID in keysDown) {
                x_rel = x_rel - clientStageParams.velocityXY;
            }
            if (upKeyID in keysDown) {
                y_rel = y_rel + clientStageParams.velocityXY;
            }
            if (downKeyID in keysDown) {
                y_rel = y_rel - clientStageParams.velocityXY;
            }
            if (pgupKeyID in keysDown) {
                z_rel = z_rel - clientStageParams.velocityZ;
            }
            if (pgdnKeyID in keysDown) {
                z_rel = z_rel + clientStageParams.velocityZ;
            }

            // Make a position request
            api.setStagePositions(x_rel, y_rel, z_rel, updatePositionValues)
        }
    }

}, false);

addEventListener("keyup", function (e) {
    delete keysDown[e.keyCode]; //Remove key from array
}, false);


