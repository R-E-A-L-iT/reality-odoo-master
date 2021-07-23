odoo.define('proquotes.fold', function (require) {
'use strict';
var publicWidget = require('web.public.widget')

publicWidget.registry.fold = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .foldInput': '_onChange',
        'change .product_foldI': '_productFoldChange',
    },
    
    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
        this._onLoad();
    },
    
    _onLoad: function () {
        var TRstyle;
        var ArrowStyle;
        var cbl = document.querySelectorAll(".foldInput");
        for(var i = 0; i < cbl.length; i++){
            var cb = cbl[i];
            if(cb.checked == true){
                TRstyle = "none";
                ArrowStyle = "rotate(90deg)";
            } else {
                TRstyle = "table-row";
                ArrowStyle = "rotate(0deg)";
            }
            var x = cb;
            while(x.tagName != "TR"){
                x = x.parentNode;
            }
            x.querySelector('.quote-folding-arrow').style.transform = ArrowStyle;
            var y = x.nextElementSibling;
            while(y != null && y != undefined){
                if(y.className.includes("is-subtotal")) {
                    break;
                } else {
                    if(y.style != undefined && y.style != null ){
                        y.style.display = TRstyle;
                    }
                }
            y = y.nextElementSibling;
            }
        }
        var subTotalList = document.getElementsByClassName("subtotal-destination");
        for(var i = 0; i < subTotalList.length; i++){
            var subTotal = subTotalList[i];
            subTotal.innerHTML = document.getElementsByClassName("subtotal-source")[i].innerHTML;
            
        }
    },
    _onChange: function (cb) {
        var TRstyle;
        var ArrowStyle;
        if(cb.currentTarget.checked == true) {
            TRstyle = "none";
            ArrowStyle = "rotate(90deg)";
        } else {
            TRstyle = "table-row";
            ArrowStyle = "rotate(0deg)";
        }
        var x = cb.currentTarget;
        while(x.tagName != "TR") {
            x = x.parentNode;
        }
        x.querySelector('.quote-folding-arrow').style.transform = ArrowStyle;
        var y = x.nextElementSibling;
        while(y != null && y != undefined) {
            if(y.className.includes("is-subtotal")) {
                break;
            } else {
                if(y.style != undefined && y.style != null){
                    y.style.display = TRstyle;
                }
            }
            y = y.nextElementSibling;
        }
        this._saveFoldStatus(cb.currentTarget);
    },
    
    _productFoldChange: function (cb) {
        this._saveFoldStatus(cb.currentTarget);
    },
    
    _saveFoldStatus: function (target) {
        var p = target;
        while(p.tagName != "TR"){
            p = p.parentNode
        }
        var s = p.querySelector(".line_id").id;
        
        return this._rpc({
            route: "/my/orders/" + this.orderDetail.orderId + "/fold/" + s,
            params: {access_token: this.orderDetail.token, checked: target.checked}});
    },
});
});
