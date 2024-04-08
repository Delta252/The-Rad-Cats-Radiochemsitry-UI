jQuery(function() {
    var socket = io.connect('http://127.0.0.1:5000');
    socket.emit('get-theme');

    socket.on('after_connect', function(msg) {
        document.getElementById("console").textContent += ("\nSocket Connection successful");
        
        if(msg.data == "offline"){
            window.location.href = './server-logoff';
        }
        else if(msg.data == "restricted"){
            $(" :input").prop("disabled", true);
        }
    });

    $("#theme").on("change", function(){
    socket.emit('send-theme', [$("#theme").val()]);
    });

    $("#update-server").click(function(){
        newID = $("#server-id").val();
        socket.emit('update-server', newID)
    });

    socket.on('update_theme', function(msg) {
        $("#theme").val(msg.data);
        document.documentElement.classList = msg.data;
    });   
});