var casper = require('casper').create({ verbose: true, logLevel: 'debug', viewportSize: { width: 2000, height: 1550 }, waitTimeout: 100000 });

casper.start();

console.log(casper.cli)
console.log(casper.cli.get(0))
console.log(casper.cli.get(1))
console.log(casper.cli.get(2))
console.log(casper.cli.get(3))

// Open the local file using file:/// protocol
casper.open('file://' + casper.cli.get(0));

casper.then(function() {
    this.capture(casper.cli.get(1));
});

casper.run();