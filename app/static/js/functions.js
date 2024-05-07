jQuery(function() {
    /* Global vars and page startup */
    const video = document.querySelector('#camera');
    var socket = io.connect('http://127.0.0.1:5000');
    var comms = false;
    var users = [];
    var href = window.location.href;
    selectedUser = '';
    adjustScroll();

    function adjustScroll() {
        if($(window).width() < 1201) {
            $("#column1").removeClass('scrollable');
            $("#column2").removeClass('scrollable');
            $("#column3").removeClass('scrollable');
            $(".content").addClass('scrollable');
        }
        else {
            $("#column1").addClass('scrollable');
            $("#column2").addClass('scrollable');
            $("#column3").addClass('scrollable');
            $(".content").removeClass('scrollable');
        }
    }

    function generateCards(data) {
        var numCol = $('.column-container').length;
        for(entry in data){
            type = data[entry][1];
            
            switch(type){
                case 'pump-peristaltic':
                    if(numCol != 2){
                        columnID = "#column1";
                    }
                    else{
                        columnID = "#column2";
                    }
                    if((href.includes('/home'))||(href.includes('/profile'))||(href.includes('/monitor'))){
                        break;
                    }
                    $(columnID).append(PeristalticPump(data[entry][0], type));
                    break;
                case 'pump-syringe':
                    if(numCol != 2){
                        columnID = "#column1";
                    }
                    else{
                        columnID = "#column2";
                    }
                    if((href.includes('/home'))||(href.includes('/profile'))||(href.includes('/monitor'))){
                        break;
                    }
                    $(columnID).append(SyringePump(data[entry][0], type));
                    break;
                case 'mixer-shutter':
                    if((href.includes('/home'))||(href.includes('/profile'))||(href.includes('/monitor'))){
                        break;
                    }
                    columnID = "#column2";
                    $(columnID).append(MixerShutter(data[entry][0], type));
                    break;
                case 'extraction':
                    if(numCol != 2){
                        columnID = "#column3";
                    }
                    else{
                        columnID = "#column2";
                    }
                    if((href.includes('/home'))||(href.includes('/profile'))||(href.includes('/monitor'))){
                        break;
                    }
                    $(columnID).append(Extractor(data[entry][0], type));
                    break;
                case 'valve':
                    if(numCol != 2){
                        columnID = "#column3";
                    }
                    else{
                        columnID = "#column2";
                    }
                    if((href.includes('/home'))||(href.includes('/profile'))||(href.includes('/monitor'))){
                        break;
                    }
                    $(columnID).append(Valve(data[entry][0], type));
                    break;
                case 'server':
                    $("#server-id").val(data[entry][0])
                    break;
                default:
                    if((href.includes('/home'))||(href.includes('/profile'))||(href.includes('/monitor'))){
                        break;
                    }
                    columnID = "#column2";
                    $(columnID).append(Card("0000", "Invalid Module", ""));
                    break;
            }
        }
    }

    function generateCmdList(data) {
        order = 1;
        for(entry in data){
            cmd = data[entry][0][0];
            if(cmd.indexOf("Wait") >= 0){
                holdType = "global";
            }
            else{
                holdType = "cmd";
            }
            $("#cmd-list").append(Cmd(order, data[entry][0][1], holdType));
            $("#hold-"+order).val(parseInt(data[entry][1]));
            order++;
        }
        $("#verify-script").css("background-color", "var(--accent)");
        $("#execute-script").attr("disabled", "disabled");
    }

    $(window).on('resize', function(){
        adjustScroll();
    });

    window.navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
            video.onloadedmetadata = (e) => {
                video.play();
            };
        })
        .catch( () => {
            $("#camera-box").append(`<img id="no-camera"></img>`);
            $("#camera").remove();
    });

    /* Begin new Addition */

    socket.on('after_connect', function(msg) {
        if(href.includes('/profile')||href.includes('/home')){}
        else{
            document.getElementById("console").textContent += ("\nSocket Connection successful");
        }        
        socket.emit('get-comms-status');
        socket.emit('get-user');
    });

    socket.on('set_user', function(msg) {
        if(href.includes('/profile')){
            currentSelectedUser = $('#username-select').val();
            $('#username-select').empty();
            username = msg.data[0];
            users = msg.data[1];
            $.each(users, function(){
                $("#username-select").append($('<option/>', {
                    value: $(this)[0], 
                    text:$(this)[0]
                }));
                if($(this)[0] == username){
                    if($(this)[1] == 'True'){
                        $("#admin-check").prop("checked", true);
                        $("#admin-check").prop("disabled", false);
                        $("#username-select").prop("disabled", false);
                        $(".admin-checkbox").css("opacity", "100%");
                    }
                    else{
                        $("#username-select").prop("disabled", true);
                        $("#admin-check").prop("checked", false);
                        $("#admin-check").prop("disabled", true);
                        $(".admin-checkbox").css("opacity", "60%");
                    }
                }
            });
            if(currentSelectedUser == null){
                $("#username-select").val(username).change();
            }
            else if(selectedUser != ''){
                $("#username-select").val(selectedUser).change();
            }
            else{
                $("#username-select").val(currentSelectedUser).change();
            }
            selectedUser = '';
            $("#new-username").val([]);
        }
        else{
            return;
        }
    });

    socket.on('update_cards', function(msg) {
        $("div.card").remove();
        generateCards(msg.data);
    });

    socket.on('serial_response', function(msg) {
        if(href.includes('/profile')||href.includes('/home')){
            return;
        }
        else{
            document.getElementById("console").textContent += ("\nSerial Response >> " + msg.data);
            $('#console').scrollTop($('#console').get(0).scrollHeight);
        }
    });

    socket.on('system_msg', function(msg) {
        if(href.includes('/profile')||href.includes('/home')){
            return;
        }
        else{
            document.getElementById("console").textContent += ("\nSystem Message >> " + msg.data);
            $('#console').scrollTop($('#console').get(0).scrollHeight);
        }
    });

    socket.on('send_comms_status', (data) => {
        success = data;
        if (success){
            comms = !comms;
        }
        document.getElementById("console").textContent += ("\nComms status: " + comms);
    });

    socket.on('set_comms', (data) => {
        success = data;
        if (success){
            comms=true;
            $("#comms-status").text("Enabled");
            $("#comms-status").css("color", "var(--green)");
            $("#toggle-comms").text("Disable Comms");
            $("#connect-beacon").css("background-color", "var(--green)");
        }
        else {
            comms=false;
            $("#comms-status").text("Disabled");
            $("#comms-status").css("color", "var(--red)");
            $("#toggle-comms").text("Enable Comms");
            $("#connect-beacon").css("background-color", "var(--red)");
        }
        $("#toggle-comms").prop("disabled",false);
    });

    socket.on('log_command', (msg) => {
        data = msg.data;
        cmd = data[0];
        transcript = data[1];
        document.getElementById("console").textContent += ("\nSent to Serial >> "+ cmd);
        $('#console').scrollTop($('#console').get(0).scrollHeight);
        document.getElementById("log-text").textContent += (transcript + "\n");
    });

    socket.on('update_cmd_list', function(msg) {
        if(href.includes('/auto')){
            $("div.cmd-entry").remove();
            generateCmdList(msg.data);
        }
    });

    socket.on('handle_verify', function(msg) {
        data = msg.data;
        success = data[0];
        msg = data[1];
        document.getElementById("console").textContent += ("\nScript verified: "+ success + "\nMsg: " + msg);
        $("#msg-popup").toggle();
        if(success == false){
            $("#verify-script").css("background-color", "var(--red)");
        }
        else{
            $("#verify-script").css("background-color", "var(--green)");
            $("#execute-script").removeAttr("disabled");
        }
    });

    socket.on('send_script', function(msg){
        filename = msg.data;
        document.location.href = filename;
    });

    socket.on('complete_execute', function(msg){
        success = msg.data;
        if(success){
            $("#verify-script").css("background-color", "var(--green)");
            $("#execute-script").removeAttr("disabled");
        }
        else{
            $("#verify-script").css("background-color", "var(--red)");
            $("#execute-script").attr("disabled", "disabled");
        }
    });

    /* UI interactions */
    $(".description-entry").on("mouseenter", function(){
        $(this).animate({height: "270px", paddingTop:"50px", paddingBottom:"50px", opacity: "100%"}, 150);
        $(this).children(".description-text").fadeIn(150);
        $(this).children(".description-goto").fadeIn(150);
        $(this).clearQueue();
    });

    $(".description-entry").on("mouseleave", function(){
        $(this).animate({height: "80px", paddingTop:"5px", paddingBottom:"5px", opacity: "75%"}, 150);
        $(this).children(".description-text").fadeOut(150);
        $(this).children(".description-goto").fadeOut(150);
        $(this).clearQueue();
    });

    $(".description-entry").on("click", function(){
        div = $(this).attr("id");
        destination = div.split("-")[1];
        switch(destination){
            case "auto":
                window.location.href = "/auto";
                break;
            case "manual":
                window.location.href = "/manual";
                break;
            case "testing":
                window.location.href = "/testing";
                break;
            case "profile":
                window.location.href = "/profile";
                break;
            case _:
                break;
        }
    });

    $(document).on('dragenter dragover drop', function (e){
        e.stopPropagation();
        e.preventDefault();
    });

    $(".content").on("click", ".delete-card", function(){
        parent = $(this).closest("div.card");
        id = parseInt(parent.attr('id').match(/\d+/));
        parent.remove();
        socket.emit('remove-device', id);
    });

    $(".content").on("click", ".apply-action", function(){
        action = $(this).val();
        parent = $(this).closest("div.card");
        var result = [];
        result.push("server");
        result.push($("#server-id").val());
        inputs = parent.find('input, select').each(function(){
            result.push($(this).val());
        });
        if(href.includes('/auto')){
            socket.emit('add-cmd-list', [action,result,'None']);
        }
        else if(href.includes('/manual')){
            socket.emit('generate-run-command', [action,result,'None']);
        }
        else{
            return;
        }
    });

    $(".content").on("click", ".remove-cmd", function(){
        parent = $(this).closest("div.cmd-entry");
        stringID = parent.find(".cmd-number").text();
        number = parseInt(stringID.match(/\d+/));
        parent.remove();
        socket.emit('remove-cmd-number', number);
    });

    $(".content").on("input", ".hold-for", function(){
        $("#verify-script").css("background-color", "var(--accent)");
        $("#execute-script").attr("disabled", "disabled");
        parent = $(this).closest("div.cmd-entry");
        stringID = parent.find(".cmd-number").text();
        number = parseInt(stringID.match(/\d+/));
        newHold = $(this).val();
        socket.emit('update-hold', [number, newHold]);
    });

    $("#add-wait").on("click", function(){
        socket.emit('add-cmd-list', ["wait", 0])
    });

    $("#verify-script").on("click", function(){
        $("#msg-popup").toggle();
        $("#msg-type").text("Verify Script");
        $("#popup-text").css("border", "none");
        $(".popup-message").html(`<h3 id="popup-text">Your script is about to be verified.<br/><br/>Would you like to download the script after success?</h3>`)
    });

    $("#upload-script").on("click", function(){
        $("#file-popup").toggle();
    });

    $("#execute-script").on("click", function(){
        socket.emit('execute-script');
        $("#execute-script").attr("disabled", "disabled");
    });

    $("#dropbox").on("dragenter dragover", function(e){
        e.stopPropagation();
        e.preventDefault();
        $("#dropbox").css("background-color",  "rgb(from var(--accent) r g b / 40%)");
    });

    $("#dropbox").on("dragleave", function(e){
        e.stopPropagation();
        e.preventDefault();
        $("#dropbox").css("background-color",  "rgb(from var(--accent) r g b / 20%)");
    });

    $("#dropbox").on("drop", function(e){
        e.stopPropagation();
        e.preventDefault();
        $("#dropbox").css("background-color",  "rgb(from var(--accent) r g b / 20%)");
        file = e.originalEvent.dataTransfer.files[0];
        $("#dropbox-text").text(file.name);
    });

    $("#dropbox").on("click", function(e){
        document.getElementById("file-input").click();
    });

    $("#clear-file").on("click", function(){
        file = '';
        $("#dropbox-text").html("Drag file here or click to <b>Upload File</b>");
    });

    $("#upload-file").on("click", function(){
        $("#dropbox-text").html("Drag file here or click to <b>Upload File</b>");
        if(file != ''){
            socket.emit('upload-file', [file.name, file])
        }
        $("#file-input").val('');
        $("#file-popup").toggle();
    });

    $("#file-input").on("change", function(){
        file = $("#file-input").prop('files')[0];
        $("#dropbox-text").text(file.name);
    });

    $("#connect-beacon").on("click", function(){
        if(comms) {
            $("#comms-status").text("Enabled");
            $("#comms-status").css("color", "var(--green)");
            $("#toggle-comms").text("Disable Comms");
        }
        else {
            $("#comms-status").text("Disabled");
            $("#comms-status").css("color", "var(--red)");
            $("#toggle-comms").text("Enable Comms");
        }
        $("#comms-popup").toggle();
    });

    $("#close-comms").on("click", function(){
        $("#comms-popup").toggle();
    });

    $("#close-msg").on("click", function(){
        $("#msg-popup").toggle();
    });

    $("#close-file").on("click", function(){
        $("#file-popup").toggle();
    });

    $("#approve-op").on("click", function(){
        type = $("#msg-type").text();
        result = new Array();
        if(type.includes('Verify Script')){
            socket.emit('verify-script',true);
        }
    });

    $("#reject-op").on("click", function(){
        type = $("#msg-type").text();
        result = new Array();
        if(type.includes('Verify Script')){
            socket.emit('verify-script',false);
        }
    });

    $("#toggle-comms").on("click", function(){
        $(this).prop("disabled",true);
        socket.emit('comms-status');
        socket.emit('toggle-comms');
    });

    $("#close-device-popup").on("click", function(){
        $("#device-popup").toggle();
    });

    $("#plus-device").on("click", function(){
        $("#device-popup").toggle();
    });

    $("#add-device").on("click", function(){
        type = $("#new-device-type").find(':selected').val();
        id = parseInt($("#new-device-id").val());
        if((type=='')||id==''){
            $("#device-message").html('Please fill out all fields.');
            return;
        }
        socket.emit('add-device', [id, type]);           
    });

    $(".content").on("change", "#valve", function(){
        if($("#valve").val() == "custom"){
            $("#valve-code").removeClass('disabled');
        }
        else{
            $("#valve-code").addClass('disabled');
        }
    });

    $("#update-user").click(function(){
        oldUsername = $("#username-select").val();
        newUsername = $("#new-username").val();
        selectedUser = newUsername;
        socket.emit('update-username', [oldUsername, newUsername]);
    });

    $("#log-off").click(function(){
        username = $("#username-select").val();
        socket.emit('log-off', username);
        location.href = "/login";
    });

    $("#username-select").on("change", function(){
        user = $("#username-select").val();
        $.each(users, function(name, admin){
            if(user == $(this)[0]){
                if($(this)[1] == 'True'){
                    $("#admin-check").prop("checked", true);
                }
                else {
                    $("#admin-check").prop("checked", false);
                }
                return false;
            }
        });
    });

    $("#admin-check").on("change", function(){
        username = $("#username-select").val();
        isAdmin = $("#admin-check").is(':checked');
        socket.emit('set-admin-status', [username, isAdmin]);
    });

    /* End New Addition */


    /* Element generation */
    var Card = function(id, name, content) { 
        return `
        <div id="card-${id}" class="card">
            <h1>${name}</h1>

            <a class="delete-card" href="#"><i class="icon icon-close"></i></a>

            <div class="input-box id-box">
                <input type="number" inputmode="integer" required="required" value="${id}" readonly>
                <span id="device-id">Device ID</span>
            </div>

            ${content}
        </div>`;
    };

    var Valve = function(id, type) {
        content = `
        <div class="input-box">
            <span class="select-label">Select an output</span>
            <div class="select">
                <select name="valve" id="valve">
                    <option selected value="1">Output 1</option>
                    <option value="2">Output 2</option>
                    <option value="3">Output 3</option>
                    <option value="4">Output 4</option>
                    <option value="5">Output 5</option>
                </select>
            </div>
        </div>
        
        <div class="optns">
            <button class="ui-btn single-btn apply-action" value="set">Set Valve</button>
        </div>`;
        return Card(id, type, content);
    };

    var PeristalticPump = function(id, type) {
        content = `
        <div class="input-box">
            <input id="pump-vol" type="number" inputmode="decimal" value=0 required="required">
            <span class="input-label">Enter a volume (mL)</span>
        </div>
        
        <div class="optns">
            <button class="ui-btn single-btn apply-action" value="pump">Start Pump</button>
        </div>`;
        return Card(id, type, content);
    };

    var SyringePump = function(id, type){
        content = `
        <div class="input-box">
            <span class="select-label">Select a syringe</span>
            <div class="select">
                <select name="pump-syringe" id="pump-syringe">
                    <option selected value="1">Eccentric 10mL</option>
                    <option value="3">Concentric 5mL</option>
                    <option value="2">Concentric 2mL (Uncalibrated)</option>
                </select>
            </div>
        </div>

        <div class="input-box">
            <input id="pump-vol" type="number" inputmode="decimal" value=0 required="required">
            <span class="input-label">Enter a volume (mL)</span>
        </div>

        <div class="optns">
            <button class="ui-btn single-btn apply-action" value="pump">Start Pump</button>
        </div>`;
        return Card(id, type, content);
    };

    var MixerShutter = function(id, type) {
        content = `
        <div class="input-box">
            <span class="select-label">Select a speed</span>
            <div class="select">
                <select name="mixer" id="mixer">
                    <option selected value="stop">Stop</option>
                    <option value="slow">Slow</option>
                    <option value="medium">Medium</option>
                    <option value="fast">Fast</option>
                </select>
            </div>
        </div>

        <div class="input-box">
            <span class="select-label">Select a direction</span>
            <div class="select">
                <select name="mixer" id="mixer">
                    <option selected value="clockwise">Clockwise</option>
                    <option value="counterclockwise">Counter-clockwise</option>
                </select>
            </div>
        </div>

        <div class="optns">
            <button class="ui-btn single-btn apply-action" value="mix">Set Mixer Speed</button>
        </div>
        
        <div class="input-box">
            <span class="select-label">Select a shutter position</span>
            <div class="select">
                <select name="shutter" id="shutter">
                    <option selected value="closed">Closed</option>
                    <option value="open">Open</option>
                    <option value="partial">Partial</option>
                </select>
            </div>
        </div>
        
        <div class="optns">
            <button class="ui-btn single-btn apply-action" value="set">Set Shutter Position</button>
        </div>`;
        return Card(id, type, content);
    }

    var Extractor = function(id, type) {
        content = `
        <div class="input-box">
            <span class="select-label">Select a slot</span>
            <div class="select">
                <select name="extraction" id="extraction">
                    <option selected value="1">Slot 1</option>
                    <option value="2">Slot 2</option>
                    <option value="3">Slot 3</option>
                    <option value="4">Slot 4</option>
                    <option value="5">Slot 5</option>
                </select>
            </div>
        </div>

        <div class="optns">
            <button class="ui-btn single-btn apply-action" value="set">Set Extractor Slot</button>
        </div>

        <div class="input-box">
            <input id="pump-vol" type="number" inputmode="decimal" value=0 required="required">
            <span class="input-label">Enter a volume (mL)</span>
        </div>

        <div class="optns">
            <button class="ui-btn single-btn apply-action" value="pump">Extract Volume</button>
        </div>`;
        return Card(id, type, content);
    };

    var Cmd = function(number, transcript, holdType) {	
        if(holdType == "cmd"){	
            labelText = "Wait for step: ";	
        }	
        else if(holdType == "global"){	
            labelText = "Wait time (s): ";	
        }	
        else {	
            labelText = "Unrecognized hold command - ";	
        }	
        content = `	
        <div class="cmd-entry">	
            <div class="cmd-data">	
                <div class="entry-info">	
                    <div class="cmd-number">[${number}]</div>	
                    <div class="cmd-text"> ${transcript} </div>	
                </div>	
                <div class="cmd-hold">	
                    <label>${labelText}</label>	
                    <span><input id="hold-${number}" class="hold-for" type="number" inputmode="integer"/></span>	
                </div>	
            </div>	
            <div class="cmd-remove">	
                <button class="remove-cmd">Remove</button>	
            </div>	
        </div>`;	
        return content;	
    } 
});