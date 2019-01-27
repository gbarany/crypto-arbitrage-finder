const Gdax = require('gdax');
var _ = require('underscore');
const BigNumber = require('bignumber.js');

// Parameters
var maxEntryCount = 3
var maxVolumeCount = Infinity
//var pairs = ['BTC-USD', 'ETH-USD']
var pairs = ['BTC-USD']

const publicClient = new Gdax.PublicClient();
const orderbookSync = new Gdax.OrderbookSync(pairs);
var asksConsolidated_old = new Array()
var bidsConsolidated_old = new Array()


function getConsolidatedOrderbook(entries) {
    var orderbook = new Array()
    var price = entries[0].price
    var size = new BigNumber(0)    
    var sizeAccumulator = 0
    for (var i = 0; i < entries.length; i++) {

        if (entries[i].price.isEqualTo(price)) {
            size = size.plus(entries[i].size)
        }
        else {
            orderbook.push([price, size])
            sizeAccumulator += size.toNumber()
            if (orderbook.length >= maxEntryCount || sizeAccumulator >= maxVolumeCount) {
                return orderbook
            }
            price = entries[i].price
            size = entries[i].size
        }
    }
}

var messageHandler = function (data) {
    try {

        if (_.isUndefined(data.product_id)) {
            return
        }
        orderbookState = orderbookSync.books[data.product_id].state()
        if (orderbookState.asks.length == 0 || orderbookState.bids.length == 0) {
            return
        }

        asksConsolidated = getConsolidatedOrderbook(orderbookState.asks)
        bidsConsolidated = getConsolidatedOrderbook(orderbookState.bids)

        if (!_.isEqual(asksConsolidated, asksConsolidated_old) || !_.isEqual(bidsConsolidated, bidsConsolidated_old)) {
            var delay = new Date().getTime() - (new Date(data.time).getTime());
            var symbol = data.product_id.replace("-", "/")


            var payload = {
                'exchange': "coinbasepro",
                "symbol": symbol,
                "data": {
                    "asks": asksConsolidated.map(x => [x[0].toNumber(),x[1].toNumber()]),
                    "bids": bidsConsolidated.map(x => [x[0].toNumber(),x[1].toNumber()])
                },
                "timestamp": new Date(data.time).getTime()
            };
            console.log(data.product_id + " asks:" + asksConsolidated.toString() + ", bids:" + bidsConsolidated.toString() + " delay:" + delay.toString() + "ms");

            asksConsolidated_old = asksConsolidated
            bidsConsolidated_old = bidsConsolidated
        }
    }
    catch (err) {
        console.log('error: ' + err)
    }
}

orderbookSync.on('message', data => { messageHandler(data) })
orderbookSync.on('error', err => { console.log(err) });