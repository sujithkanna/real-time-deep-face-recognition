var spawn = require('child_process').spawn;
var pythonProcess = spawn('python',["detect.py"]);
pythonProcess.stdout.on('data', function (data){
	console.log('Date receiving');
	console.log('from py => ', data.toString());
});
