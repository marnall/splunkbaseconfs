(window["webpackJsonp"] = window["webpackJsonp"] || []).push([[2],{

/***/ 36:
/***/ (function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function(module) {var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

/*! jQuery v3.5.0 | (c) JS Foundation and other contributors | jquery.org/license */
!function (e, t) {
  "use strict";

  "object" == ( false ? undefined : _typeof(module)) && "object" == _typeof(module.exports) ? module.exports = e.document ? t(e, !0) : function (e) {
    if (!e.document) throw new Error("jQuery requires a window with a document");
    return t(e);
  } : t(e);
}("undefined" != typeof window ? window : this, function (C, e) {
  "use strict";

  var t = [],
      r = Object.getPrototypeOf,
      s = t.slice,
      g = t.flat ? function (e) {
    return t.flat.call(e);
  } : function (e) {
    return t.concat.apply([], e);
  },
      u = t.push,
      i = t.indexOf,
      n = {},
      o = n.toString,
      v = n.hasOwnProperty,
      a = v.toString,
      l = a.call(Object),
      y = {},
      m = function m(e) {
    return "function" == typeof e && "number" != typeof e.nodeType;
  },
      x = function x(e) {
    return null != e && e === e.window;
  },
      E = C.document,
      c = {
    type: !0,
    src: !0,
    nonce: !0,
    noModule: !0
  };

  function b(e, t, n) {
    var r,
        i,
        o = (n = n || E).createElement("script");
    if (o.text = e, t) for (r in c) {
      (i = t[r] || t.getAttribute && t.getAttribute(r)) && o.setAttribute(r, i);
    }
    n.head.appendChild(o).parentNode.removeChild(o);
  }

  function w(e) {
    return null == e ? e + "" : "object" == _typeof(e) || "function" == typeof e ? n[o.call(e)] || "object" : _typeof(e);
  }

  var f = "3.5.0",
      S = function S(e, t) {
    return new S.fn.init(e, t);
  };

  function p(e) {
    var t = !!e && "length" in e && e.length,
        n = w(e);
    return !m(e) && !x(e) && ("array" === n || 0 === t || "number" == typeof t && 0 < t && t - 1 in e);
  }

  S.fn = S.prototype = {
    jquery: f,
    constructor: S,
    length: 0,
    toArray: function toArray() {
      return s.call(this);
    },
    get: function get(e) {
      return null == e ? s.call(this) : e < 0 ? this[e + this.length] : this[e];
    },
    pushStack: function pushStack(e) {
      var t = S.merge(this.constructor(), e);
      return t.prevObject = this, t;
    },
    each: function each(e) {
      return S.each(this, e);
    },
    map: function map(n) {
      return this.pushStack(S.map(this, function (e, t) {
        return n.call(e, t, e);
      }));
    },
    slice: function slice() {
      return this.pushStack(s.apply(this, arguments));
    },
    first: function first() {
      return this.eq(0);
    },
    last: function last() {
      return this.eq(-1);
    },
    even: function even() {
      return this.pushStack(S.grep(this, function (e, t) {
        return (t + 1) % 2;
      }));
    },
    odd: function odd() {
      return this.pushStack(S.grep(this, function (e, t) {
        return t % 2;
      }));
    },
    eq: function eq(e) {
      var t = this.length,
          n = +e + (e < 0 ? t : 0);
      return this.pushStack(0 <= n && n < t ? [this[n]] : []);
    },
    end: function end() {
      return this.prevObject || this.constructor();
    },
    push: u,
    sort: t.sort,
    splice: t.splice
  }, S.extend = S.fn.extend = function () {
    var e,
        t,
        n,
        r,
        i,
        o,
        a = arguments[0] || {},
        s = 1,
        u = arguments.length,
        l = !1;

    for ("boolean" == typeof a && (l = a, a = arguments[s] || {}, s++), "object" == _typeof(a) || m(a) || (a = {}), s === u && (a = this, s--); s < u; s++) {
      if (null != (e = arguments[s])) for (t in e) {
        r = e[t], "__proto__" !== t && a !== r && (l && r && (S.isPlainObject(r) || (i = Array.isArray(r))) ? (n = a[t], o = i && !Array.isArray(n) ? [] : i || S.isPlainObject(n) ? n : {}, i = !1, a[t] = S.extend(l, o, r)) : void 0 !== r && (a[t] = r));
      }
    }

    return a;
  }, S.extend({
    expando: "jQuery" + (f + Math.random()).replace(/\D/g, ""),
    isReady: !0,
    error: function error(e) {
      throw new Error(e);
    },
    noop: function noop() {},
    isPlainObject: function isPlainObject(e) {
      var t, n;
      return !(!e || "[object Object]" !== o.call(e)) && (!(t = r(e)) || "function" == typeof (n = v.call(t, "constructor") && t.constructor) && a.call(n) === l);
    },
    isEmptyObject: function isEmptyObject(e) {
      var t;

      for (t in e) {
        return !1;
      }

      return !0;
    },
    globalEval: function globalEval(e, t, n) {
      b(e, {
        nonce: t && t.nonce
      }, n);
    },
    each: function each(e, t) {
      var n,
          r = 0;

      if (p(e)) {
        for (n = e.length; r < n; r++) {
          if (!1 === t.call(e[r], r, e[r])) break;
        }
      } else for (r in e) {
        if (!1 === t.call(e[r], r, e[r])) break;
      }

      return e;
    },
    makeArray: function makeArray(e, t) {
      var n = t || [];
      return null != e && (p(Object(e)) ? S.merge(n, "string" == typeof e ? [e] : e) : u.call(n, e)), n;
    },
    inArray: function inArray(e, t, n) {
      return null == t ? -1 : i.call(t, e, n);
    },
    merge: function merge(e, t) {
      for (var n = +t.length, r = 0, i = e.length; r < n; r++) {
        e[i++] = t[r];
      }

      return e.length = i, e;
    },
    grep: function grep(e, t, n) {
      for (var r = [], i = 0, o = e.length, a = !n; i < o; i++) {
        !t(e[i], i) !== a && r.push(e[i]);
      }

      return r;
    },
    map: function map(e, t, n) {
      var r,
          i,
          o = 0,
          a = [];
      if (p(e)) for (r = e.length; o < r; o++) {
        null != (i = t(e[o], o, n)) && a.push(i);
      } else for (o in e) {
        null != (i = t(e[o], o, n)) && a.push(i);
      }
      return g(a);
    },
    guid: 1,
    support: y
  }), "function" == typeof Symbol && (S.fn[Symbol.iterator] = t[Symbol.iterator]), S.each("Boolean Number String Function Array Date RegExp Object Error Symbol".split(" "), function (e, t) {
    n["[object " + t + "]"] = t.toLowerCase();
  });

  var d = function (n) {
    var e,
        d,
        b,
        o,
        i,
        h,
        f,
        g,
        w,
        u,
        l,
        T,
        C,
        a,
        E,
        v,
        s,
        c,
        y,
        S = "sizzle" + 1 * new Date(),
        p = n.document,
        k = 0,
        r = 0,
        m = ue(),
        x = ue(),
        A = ue(),
        N = ue(),
        D = function D(e, t) {
      return e === t && (l = !0), 0;
    },
        j = {}.hasOwnProperty,
        t = [],
        q = t.pop,
        L = t.push,
        H = t.push,
        O = t.slice,
        P = function P(e, t) {
      for (var n = 0, r = e.length; n < r; n++) {
        if (e[n] === t) return n;
      }

      return -1;
    },
        R = "checked|selected|async|autofocus|autoplay|controls|defer|disabled|hidden|ismap|loop|multiple|open|readonly|required|scoped",
        M = "[\\x20\\t\\r\\n\\f]",
        I = "(?:\\\\[\\da-fA-F]{1,6}" + M + "?|\\\\[^\\r\\n\\f]|[\\w-]|[^\0-\\x7f])+",
        W = "\\[" + M + "*(" + I + ")(?:" + M + "*([*^$|!~]?=)" + M + "*(?:'((?:\\\\.|[^\\\\'])*)'|\"((?:\\\\.|[^\\\\\"])*)\"|(" + I + "))|)" + M + "*\\]",
        F = ":(" + I + ")(?:\\((('((?:\\\\.|[^\\\\'])*)'|\"((?:\\\\.|[^\\\\\"])*)\")|((?:\\\\.|[^\\\\()[\\]]|" + W + ")*)|.*)\\)|)",
        B = new RegExp(M + "+", "g"),
        $ = new RegExp("^" + M + "+|((?:^|[^\\\\])(?:\\\\.)*)" + M + "+$", "g"),
        _ = new RegExp("^" + M + "*," + M + "*"),
        z = new RegExp("^" + M + "*([>+~]|" + M + ")" + M + "*"),
        U = new RegExp(M + "|>"),
        X = new RegExp(F),
        V = new RegExp("^" + I + "$"),
        G = {
      ID: new RegExp("^#(" + I + ")"),
      CLASS: new RegExp("^\\.(" + I + ")"),
      TAG: new RegExp("^(" + I + "|[*])"),
      ATTR: new RegExp("^" + W),
      PSEUDO: new RegExp("^" + F),
      CHILD: new RegExp("^:(only|first|last|nth|nth-last)-(child|of-type)(?:\\(" + M + "*(even|odd|(([+-]|)(\\d*)n|)" + M + "*(?:([+-]|)" + M + "*(\\d+)|))" + M + "*\\)|)", "i"),
      bool: new RegExp("^(?:" + R + ")$", "i"),
      needsContext: new RegExp("^" + M + "*[>+~]|:(even|odd|eq|gt|lt|nth|first|last)(?:\\(" + M + "*((?:-\\d)?\\d*)" + M + "*\\)|)(?=[^-]|$)", "i")
    },
        Y = /HTML$/i,
        Q = /^(?:input|select|textarea|button)$/i,
        J = /^h\d$/i,
        K = /^[^{]+\{\s*\[native \w/,
        Z = /^(?:#([\w-]+)|(\w+)|\.([\w-]+))$/,
        ee = /[+~]/,
        te = new RegExp("\\\\[\\da-fA-F]{1,6}" + M + "?|\\\\([^\\r\\n\\f])", "g"),
        ne = function ne(e, t) {
      var n = "0x" + e.slice(1) - 65536;
      return t || (n < 0 ? String.fromCharCode(n + 65536) : String.fromCharCode(n >> 10 | 55296, 1023 & n | 56320));
    },
        re = /([\0-\x1f\x7f]|^-?\d)|^-$|[^\0-\x1f\x7f-\uFFFF\w-]/g,
        ie = function ie(e, t) {
      return t ? "\0" === e ? "\uFFFD" : e.slice(0, -1) + "\\" + e.charCodeAt(e.length - 1).toString(16) + " " : "\\" + e;
    },
        oe = function oe() {
      T();
    },
        ae = be(function (e) {
      return !0 === e.disabled && "fieldset" === e.nodeName.toLowerCase();
    }, {
      dir: "parentNode",
      next: "legend"
    });

    try {
      H.apply(t = O.call(p.childNodes), p.childNodes), t[p.childNodes.length].nodeType;
    } catch (e) {
      H = {
        apply: t.length ? function (e, t) {
          L.apply(e, O.call(t));
        } : function (e, t) {
          var n = e.length,
              r = 0;

          while (e[n++] = t[r++]) {
            ;
          }

          e.length = n - 1;
        }
      };
    }

    function se(t, e, n, r) {
      var i,
          o,
          a,
          s,
          u,
          l,
          c,
          f = e && e.ownerDocument,
          p = e ? e.nodeType : 9;
      if (n = n || [], "string" != typeof t || !t || 1 !== p && 9 !== p && 11 !== p) return n;

      if (!r && (T(e), e = e || C, E)) {
        if (11 !== p && (u = Z.exec(t))) if (i = u[1]) {
          if (9 === p) {
            if (!(a = e.getElementById(i))) return n;
            if (a.id === i) return n.push(a), n;
          } else if (f && (a = f.getElementById(i)) && y(e, a) && a.id === i) return n.push(a), n;
        } else {
          if (u[2]) return H.apply(n, e.getElementsByTagName(t)), n;
          if ((i = u[3]) && d.getElementsByClassName && e.getElementsByClassName) return H.apply(n, e.getElementsByClassName(i)), n;
        }

        if (d.qsa && !N[t + " "] && (!v || !v.test(t)) && (1 !== p || "object" !== e.nodeName.toLowerCase())) {
          if (c = t, f = e, 1 === p && (U.test(t) || z.test(t))) {
            (f = ee.test(t) && ye(e.parentNode) || e) === e && d.scope || ((s = e.getAttribute("id")) ? s = s.replace(re, ie) : e.setAttribute("id", s = S)), o = (l = h(t)).length;

            while (o--) {
              l[o] = (s ? "#" + s : ":scope") + " " + xe(l[o]);
            }

            c = l.join(",");
          }

          try {
            return H.apply(n, f.querySelectorAll(c)), n;
          } catch (e) {
            N(t, !0);
          } finally {
            s === S && e.removeAttribute("id");
          }
        }
      }

      return g(t.replace($, "$1"), e, n, r);
    }

    function ue() {
      var r = [];
      return function e(t, n) {
        return r.push(t + " ") > b.cacheLength && delete e[r.shift()], e[t + " "] = n;
      };
    }

    function le(e) {
      return e[S] = !0, e;
    }

    function ce(e) {
      var t = C.createElement("fieldset");

      try {
        return !!e(t);
      } catch (e) {
        return !1;
      } finally {
        t.parentNode && t.parentNode.removeChild(t), t = null;
      }
    }

    function fe(e, t) {
      var n = e.split("|"),
          r = n.length;

      while (r--) {
        b.attrHandle[n[r]] = t;
      }
    }

    function pe(e, t) {
      var n = t && e,
          r = n && 1 === e.nodeType && 1 === t.nodeType && e.sourceIndex - t.sourceIndex;
      if (r) return r;
      if (n) while (n = n.nextSibling) {
        if (n === t) return -1;
      }
      return e ? 1 : -1;
    }

    function de(t) {
      return function (e) {
        return "input" === e.nodeName.toLowerCase() && e.type === t;
      };
    }

    function he(n) {
      return function (e) {
        var t = e.nodeName.toLowerCase();
        return ("input" === t || "button" === t) && e.type === n;
      };
    }

    function ge(t) {
      return function (e) {
        return "form" in e ? e.parentNode && !1 === e.disabled ? "label" in e ? "label" in e.parentNode ? e.parentNode.disabled === t : e.disabled === t : e.isDisabled === t || e.isDisabled !== !t && ae(e) === t : e.disabled === t : "label" in e && e.disabled === t;
      };
    }

    function ve(a) {
      return le(function (o) {
        return o = +o, le(function (e, t) {
          var n,
              r = a([], e.length, o),
              i = r.length;

          while (i--) {
            e[n = r[i]] && (e[n] = !(t[n] = e[n]));
          }
        });
      });
    }

    function ye(e) {
      return e && "undefined" != typeof e.getElementsByTagName && e;
    }

    for (e in d = se.support = {}, i = se.isXML = function (e) {
      var t = e.namespaceURI,
          n = (e.ownerDocument || e).documentElement;
      return !Y.test(t || n && n.nodeName || "HTML");
    }, T = se.setDocument = function (e) {
      var t,
          n,
          r = e ? e.ownerDocument || e : p;
      return r != C && 9 === r.nodeType && r.documentElement && (a = (C = r).documentElement, E = !i(C), p != C && (n = C.defaultView) && n.top !== n && (n.addEventListener ? n.addEventListener("unload", oe, !1) : n.attachEvent && n.attachEvent("onunload", oe)), d.scope = ce(function (e) {
        return a.appendChild(e).appendChild(C.createElement("div")), "undefined" != typeof e.querySelectorAll && !e.querySelectorAll(":scope fieldset div").length;
      }), d.attributes = ce(function (e) {
        return e.className = "i", !e.getAttribute("className");
      }), d.getElementsByTagName = ce(function (e) {
        return e.appendChild(C.createComment("")), !e.getElementsByTagName("*").length;
      }), d.getElementsByClassName = K.test(C.getElementsByClassName), d.getById = ce(function (e) {
        return a.appendChild(e).id = S, !C.getElementsByName || !C.getElementsByName(S).length;
      }), d.getById ? (b.filter.ID = function (e) {
        var t = e.replace(te, ne);
        return function (e) {
          return e.getAttribute("id") === t;
        };
      }, b.find.ID = function (e, t) {
        if ("undefined" != typeof t.getElementById && E) {
          var n = t.getElementById(e);
          return n ? [n] : [];
        }
      }) : (b.filter.ID = function (e) {
        var n = e.replace(te, ne);
        return function (e) {
          var t = "undefined" != typeof e.getAttributeNode && e.getAttributeNode("id");
          return t && t.value === n;
        };
      }, b.find.ID = function (e, t) {
        if ("undefined" != typeof t.getElementById && E) {
          var n,
              r,
              i,
              o = t.getElementById(e);

          if (o) {
            if ((n = o.getAttributeNode("id")) && n.value === e) return [o];
            i = t.getElementsByName(e), r = 0;

            while (o = i[r++]) {
              if ((n = o.getAttributeNode("id")) && n.value === e) return [o];
            }
          }

          return [];
        }
      }), b.find.TAG = d.getElementsByTagName ? function (e, t) {
        return "undefined" != typeof t.getElementsByTagName ? t.getElementsByTagName(e) : d.qsa ? t.querySelectorAll(e) : void 0;
      } : function (e, t) {
        var n,
            r = [],
            i = 0,
            o = t.getElementsByTagName(e);

        if ("*" === e) {
          while (n = o[i++]) {
            1 === n.nodeType && r.push(n);
          }

          return r;
        }

        return o;
      }, b.find.CLASS = d.getElementsByClassName && function (e, t) {
        if ("undefined" != typeof t.getElementsByClassName && E) return t.getElementsByClassName(e);
      }, s = [], v = [], (d.qsa = K.test(C.querySelectorAll)) && (ce(function (e) {
        var t;
        a.appendChild(e).innerHTML = "<a id='" + S + "'></a><select id='" + S + "-\r\\' msallowcapture=''><option selected=''></option></select>", e.querySelectorAll("[msallowcapture^='']").length && v.push("[*^$]=" + M + "*(?:''|\"\")"), e.querySelectorAll("[selected]").length || v.push("\\[" + M + "*(?:value|" + R + ")"), e.querySelectorAll("[id~=" + S + "-]").length || v.push("~="), (t = C.createElement("input")).setAttribute("name", ""), e.appendChild(t), e.querySelectorAll("[name='']").length || v.push("\\[" + M + "*name" + M + "*=" + M + "*(?:''|\"\")"), e.querySelectorAll(":checked").length || v.push(":checked"), e.querySelectorAll("a#" + S + "+*").length || v.push(".#.+[+~]"), e.querySelectorAll("\\\f"), v.push("[\\r\\n\\f]");
      }), ce(function (e) {
        e.innerHTML = "<a href='' disabled='disabled'></a><select disabled='disabled'><option/></select>";
        var t = C.createElement("input");
        t.setAttribute("type", "hidden"), e.appendChild(t).setAttribute("name", "D"), e.querySelectorAll("[name=d]").length && v.push("name" + M + "*[*^$|!~]?="), 2 !== e.querySelectorAll(":enabled").length && v.push(":enabled", ":disabled"), a.appendChild(e).disabled = !0, 2 !== e.querySelectorAll(":disabled").length && v.push(":enabled", ":disabled"), e.querySelectorAll("*,:x"), v.push(",.*:");
      })), (d.matchesSelector = K.test(c = a.matches || a.webkitMatchesSelector || a.mozMatchesSelector || a.oMatchesSelector || a.msMatchesSelector)) && ce(function (e) {
        d.disconnectedMatch = c.call(e, "*"), c.call(e, "[s!='']:x"), s.push("!=", F);
      }), v = v.length && new RegExp(v.join("|")), s = s.length && new RegExp(s.join("|")), t = K.test(a.compareDocumentPosition), y = t || K.test(a.contains) ? function (e, t) {
        var n = 9 === e.nodeType ? e.documentElement : e,
            r = t && t.parentNode;
        return e === r || !(!r || 1 !== r.nodeType || !(n.contains ? n.contains(r) : e.compareDocumentPosition && 16 & e.compareDocumentPosition(r)));
      } : function (e, t) {
        if (t) while (t = t.parentNode) {
          if (t === e) return !0;
        }
        return !1;
      }, D = t ? function (e, t) {
        if (e === t) return l = !0, 0;
        var n = !e.compareDocumentPosition - !t.compareDocumentPosition;
        return n || (1 & (n = (e.ownerDocument || e) == (t.ownerDocument || t) ? e.compareDocumentPosition(t) : 1) || !d.sortDetached && t.compareDocumentPosition(e) === n ? e == C || e.ownerDocument == p && y(p, e) ? -1 : t == C || t.ownerDocument == p && y(p, t) ? 1 : u ? P(u, e) - P(u, t) : 0 : 4 & n ? -1 : 1);
      } : function (e, t) {
        if (e === t) return l = !0, 0;
        var n,
            r = 0,
            i = e.parentNode,
            o = t.parentNode,
            a = [e],
            s = [t];
        if (!i || !o) return e == C ? -1 : t == C ? 1 : i ? -1 : o ? 1 : u ? P(u, e) - P(u, t) : 0;
        if (i === o) return pe(e, t);
        n = e;

        while (n = n.parentNode) {
          a.unshift(n);
        }

        n = t;

        while (n = n.parentNode) {
          s.unshift(n);
        }

        while (a[r] === s[r]) {
          r++;
        }

        return r ? pe(a[r], s[r]) : a[r] == p ? -1 : s[r] == p ? 1 : 0;
      }), C;
    }, se.matches = function (e, t) {
      return se(e, null, null, t);
    }, se.matchesSelector = function (e, t) {
      if (T(e), d.matchesSelector && E && !N[t + " "] && (!s || !s.test(t)) && (!v || !v.test(t))) try {
        var n = c.call(e, t);
        if (n || d.disconnectedMatch || e.document && 11 !== e.document.nodeType) return n;
      } catch (e) {
        N(t, !0);
      }
      return 0 < se(t, C, null, [e]).length;
    }, se.contains = function (e, t) {
      return (e.ownerDocument || e) != C && T(e), y(e, t);
    }, se.attr = function (e, t) {
      (e.ownerDocument || e) != C && T(e);
      var n = b.attrHandle[t.toLowerCase()],
          r = n && j.call(b.attrHandle, t.toLowerCase()) ? n(e, t, !E) : void 0;
      return void 0 !== r ? r : d.attributes || !E ? e.getAttribute(t) : (r = e.getAttributeNode(t)) && r.specified ? r.value : null;
    }, se.escape = function (e) {
      return (e + "").replace(re, ie);
    }, se.error = function (e) {
      throw new Error("Syntax error, unrecognized expression: " + e);
    }, se.uniqueSort = function (e) {
      var t,
          n = [],
          r = 0,
          i = 0;

      if (l = !d.detectDuplicates, u = !d.sortStable && e.slice(0), e.sort(D), l) {
        while (t = e[i++]) {
          t === e[i] && (r = n.push(i));
        }

        while (r--) {
          e.splice(n[r], 1);
        }
      }

      return u = null, e;
    }, o = se.getText = function (e) {
      var t,
          n = "",
          r = 0,
          i = e.nodeType;

      if (i) {
        if (1 === i || 9 === i || 11 === i) {
          if ("string" == typeof e.textContent) return e.textContent;

          for (e = e.firstChild; e; e = e.nextSibling) {
            n += o(e);
          }
        } else if (3 === i || 4 === i) return e.nodeValue;
      } else while (t = e[r++]) {
        n += o(t);
      }

      return n;
    }, (b = se.selectors = {
      cacheLength: 50,
      createPseudo: le,
      match: G,
      attrHandle: {},
      find: {},
      relative: {
        ">": {
          dir: "parentNode",
          first: !0
        },
        " ": {
          dir: "parentNode"
        },
        "+": {
          dir: "previousSibling",
          first: !0
        },
        "~": {
          dir: "previousSibling"
        }
      },
      preFilter: {
        ATTR: function ATTR(e) {
          return e[1] = e[1].replace(te, ne), e[3] = (e[3] || e[4] || e[5] || "").replace(te, ne), "~=" === e[2] && (e[3] = " " + e[3] + " "), e.slice(0, 4);
        },
        CHILD: function CHILD(e) {
          return e[1] = e[1].toLowerCase(), "nth" === e[1].slice(0, 3) ? (e[3] || se.error(e[0]), e[4] = +(e[4] ? e[5] + (e[6] || 1) : 2 * ("even" === e[3] || "odd" === e[3])), e[5] = +(e[7] + e[8] || "odd" === e[3])) : e[3] && se.error(e[0]), e;
        },
        PSEUDO: function PSEUDO(e) {
          var t,
              n = !e[6] && e[2];
          return G.CHILD.test(e[0]) ? null : (e[3] ? e[2] = e[4] || e[5] || "" : n && X.test(n) && (t = h(n, !0)) && (t = n.indexOf(")", n.length - t) - n.length) && (e[0] = e[0].slice(0, t), e[2] = n.slice(0, t)), e.slice(0, 3));
        }
      },
      filter: {
        TAG: function TAG(e) {
          var t = e.replace(te, ne).toLowerCase();
          return "*" === e ? function () {
            return !0;
          } : function (e) {
            return e.nodeName && e.nodeName.toLowerCase() === t;
          };
        },
        CLASS: function CLASS(e) {
          var t = m[e + " "];
          return t || (t = new RegExp("(^|" + M + ")" + e + "(" + M + "|$)")) && m(e, function (e) {
            return t.test("string" == typeof e.className && e.className || "undefined" != typeof e.getAttribute && e.getAttribute("class") || "");
          });
        },
        ATTR: function ATTR(n, r, i) {
          return function (e) {
            var t = se.attr(e, n);
            return null == t ? "!=" === r : !r || (t += "", "=" === r ? t === i : "!=" === r ? t !== i : "^=" === r ? i && 0 === t.indexOf(i) : "*=" === r ? i && -1 < t.indexOf(i) : "$=" === r ? i && t.slice(-i.length) === i : "~=" === r ? -1 < (" " + t.replace(B, " ") + " ").indexOf(i) : "|=" === r && (t === i || t.slice(0, i.length + 1) === i + "-"));
          };
        },
        CHILD: function CHILD(h, e, t, g, v) {
          var y = "nth" !== h.slice(0, 3),
              m = "last" !== h.slice(-4),
              x = "of-type" === e;
          return 1 === g && 0 === v ? function (e) {
            return !!e.parentNode;
          } : function (e, t, n) {
            var r,
                i,
                o,
                a,
                s,
                u,
                l = y !== m ? "nextSibling" : "previousSibling",
                c = e.parentNode,
                f = x && e.nodeName.toLowerCase(),
                p = !n && !x,
                d = !1;

            if (c) {
              if (y) {
                while (l) {
                  a = e;

                  while (a = a[l]) {
                    if (x ? a.nodeName.toLowerCase() === f : 1 === a.nodeType) return !1;
                  }

                  u = l = "only" === h && !u && "nextSibling";
                }

                return !0;
              }

              if (u = [m ? c.firstChild : c.lastChild], m && p) {
                d = (s = (r = (i = (o = (a = c)[S] || (a[S] = {}))[a.uniqueID] || (o[a.uniqueID] = {}))[h] || [])[0] === k && r[1]) && r[2], a = s && c.childNodes[s];

                while (a = ++s && a && a[l] || (d = s = 0) || u.pop()) {
                  if (1 === a.nodeType && ++d && a === e) {
                    i[h] = [k, s, d];
                    break;
                  }
                }
              } else if (p && (d = s = (r = (i = (o = (a = e)[S] || (a[S] = {}))[a.uniqueID] || (o[a.uniqueID] = {}))[h] || [])[0] === k && r[1]), !1 === d) while (a = ++s && a && a[l] || (d = s = 0) || u.pop()) {
                if ((x ? a.nodeName.toLowerCase() === f : 1 === a.nodeType) && ++d && (p && ((i = (o = a[S] || (a[S] = {}))[a.uniqueID] || (o[a.uniqueID] = {}))[h] = [k, d]), a === e)) break;
              }

              return (d -= v) === g || d % g == 0 && 0 <= d / g;
            }
          };
        },
        PSEUDO: function PSEUDO(e, o) {
          var t,
              a = b.pseudos[e] || b.setFilters[e.toLowerCase()] || se.error("unsupported pseudo: " + e);
          return a[S] ? a(o) : 1 < a.length ? (t = [e, e, "", o], b.setFilters.hasOwnProperty(e.toLowerCase()) ? le(function (e, t) {
            var n,
                r = a(e, o),
                i = r.length;

            while (i--) {
              e[n = P(e, r[i])] = !(t[n] = r[i]);
            }
          }) : function (e) {
            return a(e, 0, t);
          }) : a;
        }
      },
      pseudos: {
        not: le(function (e) {
          var r = [],
              i = [],
              s = f(e.replace($, "$1"));
          return s[S] ? le(function (e, t, n, r) {
            var i,
                o = s(e, null, r, []),
                a = e.length;

            while (a--) {
              (i = o[a]) && (e[a] = !(t[a] = i));
            }
          }) : function (e, t, n) {
            return r[0] = e, s(r, null, n, i), r[0] = null, !i.pop();
          };
        }),
        has: le(function (t) {
          return function (e) {
            return 0 < se(t, e).length;
          };
        }),
        contains: le(function (t) {
          return t = t.replace(te, ne), function (e) {
            return -1 < (e.textContent || o(e)).indexOf(t);
          };
        }),
        lang: le(function (n) {
          return V.test(n || "") || se.error("unsupported lang: " + n), n = n.replace(te, ne).toLowerCase(), function (e) {
            var t;

            do {
              if (t = E ? e.lang : e.getAttribute("xml:lang") || e.getAttribute("lang")) return (t = t.toLowerCase()) === n || 0 === t.indexOf(n + "-");
            } while ((e = e.parentNode) && 1 === e.nodeType);

            return !1;
          };
        }),
        target: function target(e) {
          var t = n.location && n.location.hash;
          return t && t.slice(1) === e.id;
        },
        root: function root(e) {
          return e === a;
        },
        focus: function focus(e) {
          return e === C.activeElement && (!C.hasFocus || C.hasFocus()) && !!(e.type || e.href || ~e.tabIndex);
        },
        enabled: ge(!1),
        disabled: ge(!0),
        checked: function checked(e) {
          var t = e.nodeName.toLowerCase();
          return "input" === t && !!e.checked || "option" === t && !!e.selected;
        },
        selected: function selected(e) {
          return e.parentNode && e.parentNode.selectedIndex, !0 === e.selected;
        },
        empty: function empty(e) {
          for (e = e.firstChild; e; e = e.nextSibling) {
            if (e.nodeType < 6) return !1;
          }

          return !0;
        },
        parent: function parent(e) {
          return !b.pseudos.empty(e);
        },
        header: function header(e) {
          return J.test(e.nodeName);
        },
        input: function input(e) {
          return Q.test(e.nodeName);
        },
        button: function button(e) {
          var t = e.nodeName.toLowerCase();
          return "input" === t && "button" === e.type || "button" === t;
        },
        text: function text(e) {
          var t;
          return "input" === e.nodeName.toLowerCase() && "text" === e.type && (null == (t = e.getAttribute("type")) || "text" === t.toLowerCase());
        },
        first: ve(function () {
          return [0];
        }),
        last: ve(function (e, t) {
          return [t - 1];
        }),
        eq: ve(function (e, t, n) {
          return [n < 0 ? n + t : n];
        }),
        even: ve(function (e, t) {
          for (var n = 0; n < t; n += 2) {
            e.push(n);
          }

          return e;
        }),
        odd: ve(function (e, t) {
          for (var n = 1; n < t; n += 2) {
            e.push(n);
          }

          return e;
        }),
        lt: ve(function (e, t, n) {
          for (var r = n < 0 ? n + t : t < n ? t : n; 0 <= --r;) {
            e.push(r);
          }

          return e;
        }),
        gt: ve(function (e, t, n) {
          for (var r = n < 0 ? n + t : n; ++r < t;) {
            e.push(r);
          }

          return e;
        })
      }
    }).pseudos.nth = b.pseudos.eq, {
      radio: !0,
      checkbox: !0,
      file: !0,
      password: !0,
      image: !0
    }) {
      b.pseudos[e] = de(e);
    }

    for (e in {
      submit: !0,
      reset: !0
    }) {
      b.pseudos[e] = he(e);
    }

    function me() {}

    function xe(e) {
      for (var t = 0, n = e.length, r = ""; t < n; t++) {
        r += e[t].value;
      }

      return r;
    }

    function be(s, e, t) {
      var u = e.dir,
          l = e.next,
          c = l || u,
          f = t && "parentNode" === c,
          p = r++;
      return e.first ? function (e, t, n) {
        while (e = e[u]) {
          if (1 === e.nodeType || f) return s(e, t, n);
        }

        return !1;
      } : function (e, t, n) {
        var r,
            i,
            o,
            a = [k, p];

        if (n) {
          while (e = e[u]) {
            if ((1 === e.nodeType || f) && s(e, t, n)) return !0;
          }
        } else while (e = e[u]) {
          if (1 === e.nodeType || f) if (i = (o = e[S] || (e[S] = {}))[e.uniqueID] || (o[e.uniqueID] = {}), l && l === e.nodeName.toLowerCase()) e = e[u] || e;else {
            if ((r = i[c]) && r[0] === k && r[1] === p) return a[2] = r[2];
            if ((i[c] = a)[2] = s(e, t, n)) return !0;
          }
        }

        return !1;
      };
    }

    function we(i) {
      return 1 < i.length ? function (e, t, n) {
        var r = i.length;

        while (r--) {
          if (!i[r](e, t, n)) return !1;
        }

        return !0;
      } : i[0];
    }

    function Te(e, t, n, r, i) {
      for (var o, a = [], s = 0, u = e.length, l = null != t; s < u; s++) {
        (o = e[s]) && (n && !n(o, r, i) || (a.push(o), l && t.push(s)));
      }

      return a;
    }

    function Ce(d, h, g, v, y, e) {
      return v && !v[S] && (v = Ce(v)), y && !y[S] && (y = Ce(y, e)), le(function (e, t, n, r) {
        var i,
            o,
            a,
            s = [],
            u = [],
            l = t.length,
            c = e || function (e, t, n) {
          for (var r = 0, i = t.length; r < i; r++) {
            se(e, t[r], n);
          }

          return n;
        }(h || "*", n.nodeType ? [n] : n, []),
            f = !d || !e && h ? c : Te(c, s, d, n, r),
            p = g ? y || (e ? d : l || v) ? [] : t : f;

        if (g && g(f, p, n, r), v) {
          i = Te(p, u), v(i, [], n, r), o = i.length;

          while (o--) {
            (a = i[o]) && (p[u[o]] = !(f[u[o]] = a));
          }
        }

        if (e) {
          if (y || d) {
            if (y) {
              i = [], o = p.length;

              while (o--) {
                (a = p[o]) && i.push(f[o] = a);
              }

              y(null, p = [], i, r);
            }

            o = p.length;

            while (o--) {
              (a = p[o]) && -1 < (i = y ? P(e, a) : s[o]) && (e[i] = !(t[i] = a));
            }
          }
        } else p = Te(p === t ? p.splice(l, p.length) : p), y ? y(null, t, p, r) : H.apply(t, p);
      });
    }

    function Ee(e) {
      for (var i, t, n, r = e.length, o = b.relative[e[0].type], a = o || b.relative[" "], s = o ? 1 : 0, u = be(function (e) {
        return e === i;
      }, a, !0), l = be(function (e) {
        return -1 < P(i, e);
      }, a, !0), c = [function (e, t, n) {
        var r = !o && (n || t !== w) || ((i = t).nodeType ? u(e, t, n) : l(e, t, n));
        return i = null, r;
      }]; s < r; s++) {
        if (t = b.relative[e[s].type]) c = [be(we(c), t)];else {
          if ((t = b.filter[e[s].type].apply(null, e[s].matches))[S]) {
            for (n = ++s; n < r; n++) {
              if (b.relative[e[n].type]) break;
            }

            return Ce(1 < s && we(c), 1 < s && xe(e.slice(0, s - 1).concat({
              value: " " === e[s - 2].type ? "*" : ""
            })).replace($, "$1"), t, s < n && Ee(e.slice(s, n)), n < r && Ee(e = e.slice(n)), n < r && xe(e));
          }

          c.push(t);
        }
      }

      return we(c);
    }

    return me.prototype = b.filters = b.pseudos, b.setFilters = new me(), h = se.tokenize = function (e, t) {
      var n,
          r,
          i,
          o,
          a,
          s,
          u,
          l = x[e + " "];
      if (l) return t ? 0 : l.slice(0);
      a = e, s = [], u = b.preFilter;

      while (a) {
        for (o in n && !(r = _.exec(a)) || (r && (a = a.slice(r[0].length) || a), s.push(i = [])), n = !1, (r = z.exec(a)) && (n = r.shift(), i.push({
          value: n,
          type: r[0].replace($, " ")
        }), a = a.slice(n.length)), b.filter) {
          !(r = G[o].exec(a)) || u[o] && !(r = u[o](r)) || (n = r.shift(), i.push({
            value: n,
            type: o,
            matches: r
          }), a = a.slice(n.length));
        }

        if (!n) break;
      }

      return t ? a.length : a ? se.error(e) : x(e, s).slice(0);
    }, f = se.compile = function (e, t) {
      var n,
          v,
          y,
          m,
          x,
          r,
          i = [],
          o = [],
          a = A[e + " "];

      if (!a) {
        t || (t = h(e)), n = t.length;

        while (n--) {
          (a = Ee(t[n]))[S] ? i.push(a) : o.push(a);
        }

        (a = A(e, (v = o, m = 0 < (y = i).length, x = 0 < v.length, r = function r(e, t, n, _r, i) {
          var o,
              a,
              s,
              u = 0,
              l = "0",
              c = e && [],
              f = [],
              p = w,
              d = e || x && b.find.TAG("*", i),
              h = k += null == p ? 1 : Math.random() || .1,
              g = d.length;

          for (i && (w = t == C || t || i); l !== g && null != (o = d[l]); l++) {
            if (x && o) {
              a = 0, t || o.ownerDocument == C || (T(o), n = !E);

              while (s = v[a++]) {
                if (s(o, t || C, n)) {
                  _r.push(o);

                  break;
                }
              }

              i && (k = h);
            }

            m && ((o = !s && o) && u--, e && c.push(o));
          }

          if (u += l, m && l !== u) {
            a = 0;

            while (s = y[a++]) {
              s(c, f, t, n);
            }

            if (e) {
              if (0 < u) while (l--) {
                c[l] || f[l] || (f[l] = q.call(_r));
              }
              f = Te(f);
            }

            H.apply(_r, f), i && !e && 0 < f.length && 1 < u + y.length && se.uniqueSort(_r);
          }

          return i && (k = h, w = p), c;
        }, m ? le(r) : r))).selector = e;
      }

      return a;
    }, g = se.select = function (e, t, n, r) {
      var i,
          o,
          a,
          s,
          u,
          l = "function" == typeof e && e,
          c = !r && h(e = l.selector || e);

      if (n = n || [], 1 === c.length) {
        if (2 < (o = c[0] = c[0].slice(0)).length && "ID" === (a = o[0]).type && 9 === t.nodeType && E && b.relative[o[1].type]) {
          if (!(t = (b.find.ID(a.matches[0].replace(te, ne), t) || [])[0])) return n;
          l && (t = t.parentNode), e = e.slice(o.shift().value.length);
        }

        i = G.needsContext.test(e) ? 0 : o.length;

        while (i--) {
          if (a = o[i], b.relative[s = a.type]) break;

          if ((u = b.find[s]) && (r = u(a.matches[0].replace(te, ne), ee.test(o[0].type) && ye(t.parentNode) || t))) {
            if (o.splice(i, 1), !(e = r.length && xe(o))) return H.apply(n, r), n;
            break;
          }
        }
      }

      return (l || f(e, c))(r, t, !E, n, !t || ee.test(e) && ye(t.parentNode) || t), n;
    }, d.sortStable = S.split("").sort(D).join("") === S, d.detectDuplicates = !!l, T(), d.sortDetached = ce(function (e) {
      return 1 & e.compareDocumentPosition(C.createElement("fieldset"));
    }), ce(function (e) {
      return e.innerHTML = "<a href='#'></a>", "#" === e.firstChild.getAttribute("href");
    }) || fe("type|href|height|width", function (e, t, n) {
      if (!n) return e.getAttribute(t, "type" === t.toLowerCase() ? 1 : 2);
    }), d.attributes && ce(function (e) {
      return e.innerHTML = "<input/>", e.firstChild.setAttribute("value", ""), "" === e.firstChild.getAttribute("value");
    }) || fe("value", function (e, t, n) {
      if (!n && "input" === e.nodeName.toLowerCase()) return e.defaultValue;
    }), ce(function (e) {
      return null == e.getAttribute("disabled");
    }) || fe(R, function (e, t, n) {
      var r;
      if (!n) return !0 === e[t] ? t.toLowerCase() : (r = e.getAttributeNode(t)) && r.specified ? r.value : null;
    }), se;
  }(C);

  S.find = d, S.expr = d.selectors, S.expr[":"] = S.expr.pseudos, S.uniqueSort = S.unique = d.uniqueSort, S.text = d.getText, S.isXMLDoc = d.isXML, S.contains = d.contains, S.escapeSelector = d.escape;

  var h = function h(e, t, n) {
    var r = [],
        i = void 0 !== n;

    while ((e = e[t]) && 9 !== e.nodeType) {
      if (1 === e.nodeType) {
        if (i && S(e).is(n)) break;
        r.push(e);
      }
    }

    return r;
  },
      T = function T(e, t) {
    for (var n = []; e; e = e.nextSibling) {
      1 === e.nodeType && e !== t && n.push(e);
    }

    return n;
  },
      k = S.expr.match.needsContext;

  function A(e, t) {
    return e.nodeName && e.nodeName.toLowerCase() === t.toLowerCase();
  }

  var N = /^<([a-z][^\/\0>:\x20\t\r\n\f]*)[\x20\t\r\n\f]*\/?>(?:<\/\1>|)$/i;

  function D(e, n, r) {
    return m(n) ? S.grep(e, function (e, t) {
      return !!n.call(e, t, e) !== r;
    }) : n.nodeType ? S.grep(e, function (e) {
      return e === n !== r;
    }) : "string" != typeof n ? S.grep(e, function (e) {
      return -1 < i.call(n, e) !== r;
    }) : S.filter(n, e, r);
  }

  S.filter = function (e, t, n) {
    var r = t[0];
    return n && (e = ":not(" + e + ")"), 1 === t.length && 1 === r.nodeType ? S.find.matchesSelector(r, e) ? [r] : [] : S.find.matches(e, S.grep(t, function (e) {
      return 1 === e.nodeType;
    }));
  }, S.fn.extend({
    find: function find(e) {
      var t,
          n,
          r = this.length,
          i = this;
      if ("string" != typeof e) return this.pushStack(S(e).filter(function () {
        for (t = 0; t < r; t++) {
          if (S.contains(i[t], this)) return !0;
        }
      }));

      for (n = this.pushStack([]), t = 0; t < r; t++) {
        S.find(e, i[t], n);
      }

      return 1 < r ? S.uniqueSort(n) : n;
    },
    filter: function filter(e) {
      return this.pushStack(D(this, e || [], !1));
    },
    not: function not(e) {
      return this.pushStack(D(this, e || [], !0));
    },
    is: function is(e) {
      return !!D(this, "string" == typeof e && k.test(e) ? S(e) : e || [], !1).length;
    }
  });
  var j,
      q = /^(?:\s*(<[\w\W]+>)[^>]*|#([\w-]+))$/;
  (S.fn.init = function (e, t, n) {
    var r, i;
    if (!e) return this;

    if (n = n || j, "string" == typeof e) {
      if (!(r = "<" === e[0] && ">" === e[e.length - 1] && 3 <= e.length ? [null, e, null] : q.exec(e)) || !r[1] && t) return !t || t.jquery ? (t || n).find(e) : this.constructor(t).find(e);

      if (r[1]) {
        if (t = t instanceof S ? t[0] : t, S.merge(this, S.parseHTML(r[1], t && t.nodeType ? t.ownerDocument || t : E, !0)), N.test(r[1]) && S.isPlainObject(t)) for (r in t) {
          m(this[r]) ? this[r](t[r]) : this.attr(r, t[r]);
        }
        return this;
      }

      return (i = E.getElementById(r[2])) && (this[0] = i, this.length = 1), this;
    }

    return e.nodeType ? (this[0] = e, this.length = 1, this) : m(e) ? void 0 !== n.ready ? n.ready(e) : e(S) : S.makeArray(e, this);
  }).prototype = S.fn, j = S(E);
  var L = /^(?:parents|prev(?:Until|All))/,
      H = {
    children: !0,
    contents: !0,
    next: !0,
    prev: !0
  };

  function O(e, t) {
    while ((e = e[t]) && 1 !== e.nodeType) {
      ;
    }

    return e;
  }

  S.fn.extend({
    has: function has(e) {
      var t = S(e, this),
          n = t.length;
      return this.filter(function () {
        for (var e = 0; e < n; e++) {
          if (S.contains(this, t[e])) return !0;
        }
      });
    },
    closest: function closest(e, t) {
      var n,
          r = 0,
          i = this.length,
          o = [],
          a = "string" != typeof e && S(e);
      if (!k.test(e)) for (; r < i; r++) {
        for (n = this[r]; n && n !== t; n = n.parentNode) {
          if (n.nodeType < 11 && (a ? -1 < a.index(n) : 1 === n.nodeType && S.find.matchesSelector(n, e))) {
            o.push(n);
            break;
          }
        }
      }
      return this.pushStack(1 < o.length ? S.uniqueSort(o) : o);
    },
    index: function index(e) {
      return e ? "string" == typeof e ? i.call(S(e), this[0]) : i.call(this, e.jquery ? e[0] : e) : this[0] && this[0].parentNode ? this.first().prevAll().length : -1;
    },
    add: function add(e, t) {
      return this.pushStack(S.uniqueSort(S.merge(this.get(), S(e, t))));
    },
    addBack: function addBack(e) {
      return this.add(null == e ? this.prevObject : this.prevObject.filter(e));
    }
  }), S.each({
    parent: function parent(e) {
      var t = e.parentNode;
      return t && 11 !== t.nodeType ? t : null;
    },
    parents: function parents(e) {
      return h(e, "parentNode");
    },
    parentsUntil: function parentsUntil(e, t, n) {
      return h(e, "parentNode", n);
    },
    next: function next(e) {
      return O(e, "nextSibling");
    },
    prev: function prev(e) {
      return O(e, "previousSibling");
    },
    nextAll: function nextAll(e) {
      return h(e, "nextSibling");
    },
    prevAll: function prevAll(e) {
      return h(e, "previousSibling");
    },
    nextUntil: function nextUntil(e, t, n) {
      return h(e, "nextSibling", n);
    },
    prevUntil: function prevUntil(e, t, n) {
      return h(e, "previousSibling", n);
    },
    siblings: function siblings(e) {
      return T((e.parentNode || {}).firstChild, e);
    },
    children: function children(e) {
      return T(e.firstChild);
    },
    contents: function contents(e) {
      return null != e.contentDocument && r(e.contentDocument) ? e.contentDocument : (A(e, "template") && (e = e.content || e), S.merge([], e.childNodes));
    }
  }, function (r, i) {
    S.fn[r] = function (e, t) {
      var n = S.map(this, i, e);
      return "Until" !== r.slice(-5) && (t = e), t && "string" == typeof t && (n = S.filter(t, n)), 1 < this.length && (H[r] || S.uniqueSort(n), L.test(r) && n.reverse()), this.pushStack(n);
    };
  });
  var P = /[^\x20\t\r\n\f]+/g;

  function R(e) {
    return e;
  }

  function M(e) {
    throw e;
  }

  function I(e, t, n, r) {
    var i;

    try {
      e && m(i = e.promise) ? i.call(e).done(t).fail(n) : e && m(i = e.then) ? i.call(e, t, n) : t.apply(void 0, [e].slice(r));
    } catch (e) {
      n.apply(void 0, [e]);
    }
  }

  S.Callbacks = function (r) {
    var e, n;
    r = "string" == typeof r ? (e = r, n = {}, S.each(e.match(P) || [], function (e, t) {
      n[t] = !0;
    }), n) : S.extend({}, r);

    var i,
        t,
        o,
        a,
        s = [],
        u = [],
        l = -1,
        c = function c() {
      for (a = a || r.once, o = i = !0; u.length; l = -1) {
        t = u.shift();

        while (++l < s.length) {
          !1 === s[l].apply(t[0], t[1]) && r.stopOnFalse && (l = s.length, t = !1);
        }
      }

      r.memory || (t = !1), i = !1, a && (s = t ? [] : "");
    },
        f = {
      add: function add() {
        return s && (t && !i && (l = s.length - 1, u.push(t)), function n(e) {
          S.each(e, function (e, t) {
            m(t) ? r.unique && f.has(t) || s.push(t) : t && t.length && "string" !== w(t) && n(t);
          });
        }(arguments), t && !i && c()), this;
      },
      remove: function remove() {
        return S.each(arguments, function (e, t) {
          var n;

          while (-1 < (n = S.inArray(t, s, n))) {
            s.splice(n, 1), n <= l && l--;
          }
        }), this;
      },
      has: function has(e) {
        return e ? -1 < S.inArray(e, s) : 0 < s.length;
      },
      empty: function empty() {
        return s && (s = []), this;
      },
      disable: function disable() {
        return a = u = [], s = t = "", this;
      },
      disabled: function disabled() {
        return !s;
      },
      lock: function lock() {
        return a = u = [], t || i || (s = t = ""), this;
      },
      locked: function locked() {
        return !!a;
      },
      fireWith: function fireWith(e, t) {
        return a || (t = [e, (t = t || []).slice ? t.slice() : t], u.push(t), i || c()), this;
      },
      fire: function fire() {
        return f.fireWith(this, arguments), this;
      },
      fired: function fired() {
        return !!o;
      }
    };

    return f;
  }, S.extend({
    Deferred: function Deferred(e) {
      var o = [["notify", "progress", S.Callbacks("memory"), S.Callbacks("memory"), 2], ["resolve", "done", S.Callbacks("once memory"), S.Callbacks("once memory"), 0, "resolved"], ["reject", "fail", S.Callbacks("once memory"), S.Callbacks("once memory"), 1, "rejected"]],
          i = "pending",
          a = {
        state: function state() {
          return i;
        },
        always: function always() {
          return s.done(arguments).fail(arguments), this;
        },
        "catch": function _catch(e) {
          return a.then(null, e);
        },
        pipe: function pipe() {
          var i = arguments;
          return S.Deferred(function (r) {
            S.each(o, function (e, t) {
              var n = m(i[t[4]]) && i[t[4]];
              s[t[1]](function () {
                var e = n && n.apply(this, arguments);
                e && m(e.promise) ? e.promise().progress(r.notify).done(r.resolve).fail(r.reject) : r[t[0] + "With"](this, n ? [e] : arguments);
              });
            }), i = null;
          }).promise();
        },
        then: function then(t, n, r) {
          var u = 0;

          function l(i, o, a, s) {
            return function () {
              var n = this,
                  r = arguments,
                  e = function e() {
                var e, t;

                if (!(i < u)) {
                  if ((e = a.apply(n, r)) === o.promise()) throw new TypeError("Thenable self-resolution");
                  t = e && ("object" == _typeof(e) || "function" == typeof e) && e.then, m(t) ? s ? t.call(e, l(u, o, R, s), l(u, o, M, s)) : (u++, t.call(e, l(u, o, R, s), l(u, o, M, s), l(u, o, R, o.notifyWith))) : (a !== R && (n = void 0, r = [e]), (s || o.resolveWith)(n, r));
                }
              },
                  t = s ? e : function () {
                try {
                  e();
                } catch (e) {
                  S.Deferred.exceptionHook && S.Deferred.exceptionHook(e, t.stackTrace), u <= i + 1 && (a !== M && (n = void 0, r = [e]), o.rejectWith(n, r));
                }
              };

              i ? t() : (S.Deferred.getStackHook && (t.stackTrace = S.Deferred.getStackHook()), C.setTimeout(t));
            };
          }

          return S.Deferred(function (e) {
            o[0][3].add(l(0, e, m(r) ? r : R, e.notifyWith)), o[1][3].add(l(0, e, m(t) ? t : R)), o[2][3].add(l(0, e, m(n) ? n : M));
          }).promise();
        },
        promise: function promise(e) {
          return null != e ? S.extend(e, a) : a;
        }
      },
          s = {};
      return S.each(o, function (e, t) {
        var n = t[2],
            r = t[5];
        a[t[1]] = n.add, r && n.add(function () {
          i = r;
        }, o[3 - e][2].disable, o[3 - e][3].disable, o[0][2].lock, o[0][3].lock), n.add(t[3].fire), s[t[0]] = function () {
          return s[t[0] + "With"](this === s ? void 0 : this, arguments), this;
        }, s[t[0] + "With"] = n.fireWith;
      }), a.promise(s), e && e.call(s, s), s;
    },
    when: function when(e) {
      var n = arguments.length,
          t = n,
          r = Array(t),
          i = s.call(arguments),
          o = S.Deferred(),
          a = function a(t) {
        return function (e) {
          r[t] = this, i[t] = 1 < arguments.length ? s.call(arguments) : e, --n || o.resolveWith(r, i);
        };
      };

      if (n <= 1 && (I(e, o.done(a(t)).resolve, o.reject, !n), "pending" === o.state() || m(i[t] && i[t].then))) return o.then();

      while (t--) {
        I(i[t], a(t), o.reject);
      }

      return o.promise();
    }
  });
  var W = /^(Eval|Internal|Range|Reference|Syntax|Type|URI)Error$/;
  S.Deferred.exceptionHook = function (e, t) {
    C.console && C.console.warn && e && W.test(e.name) && C.console.warn("jQuery.Deferred exception: " + e.message, e.stack, t);
  }, S.readyException = function (e) {
    C.setTimeout(function () {
      throw e;
    });
  };
  var F = S.Deferred();

  function B() {
    E.removeEventListener("DOMContentLoaded", B), C.removeEventListener("load", B), S.ready();
  }

  S.fn.ready = function (e) {
    return F.then(e)["catch"](function (e) {
      S.readyException(e);
    }), this;
  }, S.extend({
    isReady: !1,
    readyWait: 1,
    ready: function ready(e) {
      (!0 === e ? --S.readyWait : S.isReady) || (S.isReady = !0) !== e && 0 < --S.readyWait || F.resolveWith(E, [S]);
    }
  }), S.ready.then = F.then, "complete" === E.readyState || "loading" !== E.readyState && !E.documentElement.doScroll ? C.setTimeout(S.ready) : (E.addEventListener("DOMContentLoaded", B), C.addEventListener("load", B));

  var $ = function $(e, t, n, r, i, o, a) {
    var s = 0,
        u = e.length,
        l = null == n;
    if ("object" === w(n)) for (s in i = !0, n) {
      $(e, t, s, n[s], !0, o, a);
    } else if (void 0 !== r && (i = !0, m(r) || (a = !0), l && (a ? (t.call(e, r), t = null) : (l = t, t = function t(e, _t2, n) {
      return l.call(S(e), n);
    })), t)) for (; s < u; s++) {
      t(e[s], n, a ? r : r.call(e[s], s, t(e[s], n)));
    }
    return i ? e : l ? t.call(e) : u ? t(e[0], n) : o;
  },
      _ = /^-ms-/,
      z = /-([a-z])/g;

  function U(e, t) {
    return t.toUpperCase();
  }

  function X(e) {
    return e.replace(_, "ms-").replace(z, U);
  }

  var V = function V(e) {
    return 1 === e.nodeType || 9 === e.nodeType || !+e.nodeType;
  };

  function G() {
    this.expando = S.expando + G.uid++;
  }

  G.uid = 1, G.prototype = {
    cache: function cache(e) {
      var t = e[this.expando];
      return t || (t = Object.create(null), V(e) && (e.nodeType ? e[this.expando] = t : Object.defineProperty(e, this.expando, {
        value: t,
        configurable: !0
      }))), t;
    },
    set: function set(e, t, n) {
      var r,
          i = this.cache(e);
      if ("string" == typeof t) i[X(t)] = n;else for (r in t) {
        i[X(r)] = t[r];
      }
      return i;
    },
    get: function get(e, t) {
      return void 0 === t ? this.cache(e) : e[this.expando] && e[this.expando][X(t)];
    },
    access: function access(e, t, n) {
      return void 0 === t || t && "string" == typeof t && void 0 === n ? this.get(e, t) : (this.set(e, t, n), void 0 !== n ? n : t);
    },
    remove: function remove(e, t) {
      var n,
          r = e[this.expando];

      if (void 0 !== r) {
        if (void 0 !== t) {
          n = (t = Array.isArray(t) ? t.map(X) : (t = X(t)) in r ? [t] : t.match(P) || []).length;

          while (n--) {
            delete r[t[n]];
          }
        }

        (void 0 === t || S.isEmptyObject(r)) && (e.nodeType ? e[this.expando] = void 0 : delete e[this.expando]);
      }
    },
    hasData: function hasData(e) {
      var t = e[this.expando];
      return void 0 !== t && !S.isEmptyObject(t);
    }
  };
  var Y = new G(),
      Q = new G(),
      J = /^(?:\{[\w\W]*\}|\[[\w\W]*\])$/,
      K = /[A-Z]/g;

  function Z(e, t, n) {
    var r, i;
    if (void 0 === n && 1 === e.nodeType) if (r = "data-" + t.replace(K, "-$&").toLowerCase(), "string" == typeof (n = e.getAttribute(r))) {
      try {
        n = "true" === (i = n) || "false" !== i && ("null" === i ? null : i === +i + "" ? +i : J.test(i) ? JSON.parse(i) : i);
      } catch (e) {}

      Q.set(e, t, n);
    } else n = void 0;
    return n;
  }

  S.extend({
    hasData: function hasData(e) {
      return Q.hasData(e) || Y.hasData(e);
    },
    data: function data(e, t, n) {
      return Q.access(e, t, n);
    },
    removeData: function removeData(e, t) {
      Q.remove(e, t);
    },
    _data: function _data(e, t, n) {
      return Y.access(e, t, n);
    },
    _removeData: function _removeData(e, t) {
      Y.remove(e, t);
    }
  }), S.fn.extend({
    data: function data(n, e) {
      var t,
          r,
          i,
          o = this[0],
          a = o && o.attributes;

      if (void 0 === n) {
        if (this.length && (i = Q.get(o), 1 === o.nodeType && !Y.get(o, "hasDataAttrs"))) {
          t = a.length;

          while (t--) {
            a[t] && 0 === (r = a[t].name).indexOf("data-") && (r = X(r.slice(5)), Z(o, r, i[r]));
          }

          Y.set(o, "hasDataAttrs", !0);
        }

        return i;
      }

      return "object" == _typeof(n) ? this.each(function () {
        Q.set(this, n);
      }) : $(this, function (e) {
        var t;
        if (o && void 0 === e) return void 0 !== (t = Q.get(o, n)) ? t : void 0 !== (t = Z(o, n)) ? t : void 0;
        this.each(function () {
          Q.set(this, n, e);
        });
      }, null, e, 1 < arguments.length, null, !0);
    },
    removeData: function removeData(e) {
      return this.each(function () {
        Q.remove(this, e);
      });
    }
  }), S.extend({
    queue: function queue(e, t, n) {
      var r;
      if (e) return t = (t || "fx") + "queue", r = Y.get(e, t), n && (!r || Array.isArray(n) ? r = Y.access(e, t, S.makeArray(n)) : r.push(n)), r || [];
    },
    dequeue: function dequeue(e, t) {
      t = t || "fx";

      var n = S.queue(e, t),
          r = n.length,
          i = n.shift(),
          o = S._queueHooks(e, t);

      "inprogress" === i && (i = n.shift(), r--), i && ("fx" === t && n.unshift("inprogress"), delete o.stop, i.call(e, function () {
        S.dequeue(e, t);
      }, o)), !r && o && o.empty.fire();
    },
    _queueHooks: function _queueHooks(e, t) {
      var n = t + "queueHooks";
      return Y.get(e, n) || Y.access(e, n, {
        empty: S.Callbacks("once memory").add(function () {
          Y.remove(e, [t + "queue", n]);
        })
      });
    }
  }), S.fn.extend({
    queue: function queue(t, n) {
      var e = 2;
      return "string" != typeof t && (n = t, t = "fx", e--), arguments.length < e ? S.queue(this[0], t) : void 0 === n ? this : this.each(function () {
        var e = S.queue(this, t, n);
        S._queueHooks(this, t), "fx" === t && "inprogress" !== e[0] && S.dequeue(this, t);
      });
    },
    dequeue: function dequeue(e) {
      return this.each(function () {
        S.dequeue(this, e);
      });
    },
    clearQueue: function clearQueue(e) {
      return this.queue(e || "fx", []);
    },
    promise: function promise(e, t) {
      var n,
          r = 1,
          i = S.Deferred(),
          o = this,
          a = this.length,
          s = function s() {
        --r || i.resolveWith(o, [o]);
      };

      "string" != typeof e && (t = e, e = void 0), e = e || "fx";

      while (a--) {
        (n = Y.get(o[a], e + "queueHooks")) && n.empty && (r++, n.empty.add(s));
      }

      return s(), i.promise(t);
    }
  });

  var ee = /[+-]?(?:\d*\.|)\d+(?:[eE][+-]?\d+|)/.source,
      te = new RegExp("^(?:([+-])=|)(" + ee + ")([a-z%]*)$", "i"),
      ne = ["Top", "Right", "Bottom", "Left"],
      re = E.documentElement,
      ie = function ie(e) {
    return S.contains(e.ownerDocument, e);
  },
      oe = {
    composed: !0
  };

  re.getRootNode && (ie = function ie(e) {
    return S.contains(e.ownerDocument, e) || e.getRootNode(oe) === e.ownerDocument;
  });

  var ae = function ae(e, t) {
    return "none" === (e = t || e).style.display || "" === e.style.display && ie(e) && "none" === S.css(e, "display");
  };

  function se(e, t, n, r) {
    var i,
        o,
        a = 20,
        s = r ? function () {
      return r.cur();
    } : function () {
      return S.css(e, t, "");
    },
        u = s(),
        l = n && n[3] || (S.cssNumber[t] ? "" : "px"),
        c = e.nodeType && (S.cssNumber[t] || "px" !== l && +u) && te.exec(S.css(e, t));

    if (c && c[3] !== l) {
      u /= 2, l = l || c[3], c = +u || 1;

      while (a--) {
        S.style(e, t, c + l), (1 - o) * (1 - (o = s() / u || .5)) <= 0 && (a = 0), c /= o;
      }

      c *= 2, S.style(e, t, c + l), n = n || [];
    }

    return n && (c = +c || +u || 0, i = n[1] ? c + (n[1] + 1) * n[2] : +n[2], r && (r.unit = l, r.start = c, r.end = i)), i;
  }

  var ue = {};

  function le(e, t) {
    for (var n, r, i, o, a, s, u, l = [], c = 0, f = e.length; c < f; c++) {
      (r = e[c]).style && (n = r.style.display, t ? ("none" === n && (l[c] = Y.get(r, "display") || null, l[c] || (r.style.display = "")), "" === r.style.display && ae(r) && (l[c] = (u = a = o = void 0, a = (i = r).ownerDocument, s = i.nodeName, (u = ue[s]) || (o = a.body.appendChild(a.createElement(s)), u = S.css(o, "display"), o.parentNode.removeChild(o), "none" === u && (u = "block"), ue[s] = u)))) : "none" !== n && (l[c] = "none", Y.set(r, "display", n)));
    }

    for (c = 0; c < f; c++) {
      null != l[c] && (e[c].style.display = l[c]);
    }

    return e;
  }

  S.fn.extend({
    show: function show() {
      return le(this, !0);
    },
    hide: function hide() {
      return le(this);
    },
    toggle: function toggle(e) {
      return "boolean" == typeof e ? e ? this.show() : this.hide() : this.each(function () {
        ae(this) ? S(this).show() : S(this).hide();
      });
    }
  });
  var ce,
      fe,
      pe = /^(?:checkbox|radio)$/i,
      de = /<([a-z][^\/\0>\x20\t\r\n\f]*)/i,
      he = /^$|^module$|\/(?:java|ecma)script/i;
  ce = E.createDocumentFragment().appendChild(E.createElement("div")), (fe = E.createElement("input")).setAttribute("type", "radio"), fe.setAttribute("checked", "checked"), fe.setAttribute("name", "t"), ce.appendChild(fe), y.checkClone = ce.cloneNode(!0).cloneNode(!0).lastChild.checked, ce.innerHTML = "<textarea>x</textarea>", y.noCloneChecked = !!ce.cloneNode(!0).lastChild.defaultValue, ce.innerHTML = "<option></option>", y.option = !!ce.lastChild;
  var ge = {
    thead: [1, "<table>", "</table>"],
    col: [2, "<table><colgroup>", "</colgroup></table>"],
    tr: [2, "<table><tbody>", "</tbody></table>"],
    td: [3, "<table><tbody><tr>", "</tr></tbody></table>"],
    _default: [0, "", ""]
  };

  function ve(e, t) {
    var n;
    return n = "undefined" != typeof e.getElementsByTagName ? e.getElementsByTagName(t || "*") : "undefined" != typeof e.querySelectorAll ? e.querySelectorAll(t || "*") : [], void 0 === t || t && A(e, t) ? S.merge([e], n) : n;
  }

  function ye(e, t) {
    for (var n = 0, r = e.length; n < r; n++) {
      Y.set(e[n], "globalEval", !t || Y.get(t[n], "globalEval"));
    }
  }

  ge.tbody = ge.tfoot = ge.colgroup = ge.caption = ge.thead, ge.th = ge.td, y.option || (ge.optgroup = ge.option = [1, "<select multiple='multiple'>", "</select>"]);
  var me = /<|&#?\w+;/;

  function xe(e, t, n, r, i) {
    for (var o, a, s, u, l, c, f = t.createDocumentFragment(), p = [], d = 0, h = e.length; d < h; d++) {
      if ((o = e[d]) || 0 === o) if ("object" === w(o)) S.merge(p, o.nodeType ? [o] : o);else if (me.test(o)) {
        a = a || f.appendChild(t.createElement("div")), s = (de.exec(o) || ["", ""])[1].toLowerCase(), u = ge[s] || ge._default, a.innerHTML = u[1] + S.htmlPrefilter(o) + u[2], c = u[0];

        while (c--) {
          a = a.lastChild;
        }

        S.merge(p, a.childNodes), (a = f.firstChild).textContent = "";
      } else p.push(t.createTextNode(o));
    }

    f.textContent = "", d = 0;

    while (o = p[d++]) {
      if (r && -1 < S.inArray(o, r)) i && i.push(o);else if (l = ie(o), a = ve(f.appendChild(o), "script"), l && ye(a), n) {
        c = 0;

        while (o = a[c++]) {
          he.test(o.type || "") && n.push(o);
        }
      }
    }

    return f;
  }

  var be = /^key/,
      we = /^(?:mouse|pointer|contextmenu|drag|drop)|click/,
      Te = /^([^.]*)(?:\.(.+)|)/;

  function Ce() {
    return !0;
  }

  function Ee() {
    return !1;
  }

  function Se(e, t) {
    return e === function () {
      try {
        return E.activeElement;
      } catch (e) {}
    }() == ("focus" === t);
  }

  function ke(e, t, n, r, i, o) {
    var a, s;

    if ("object" == _typeof(t)) {
      for (s in "string" != typeof n && (r = r || n, n = void 0), t) {
        ke(e, s, n, r, t[s], o);
      }

      return e;
    }

    if (null == r && null == i ? (i = n, r = n = void 0) : null == i && ("string" == typeof n ? (i = r, r = void 0) : (i = r, r = n, n = void 0)), !1 === i) i = Ee;else if (!i) return e;
    return 1 === o && (a = i, (i = function i(e) {
      return S().off(e), a.apply(this, arguments);
    }).guid = a.guid || (a.guid = S.guid++)), e.each(function () {
      S.event.add(this, t, i, r, n);
    });
  }

  function Ae(e, i, o) {
    o ? (Y.set(e, i, !1), S.event.add(e, i, {
      namespace: !1,
      handler: function handler(e) {
        var t,
            n,
            r = Y.get(this, i);

        if (1 & e.isTrigger && this[i]) {
          if (r.length) (S.event.special[i] || {}).delegateType && e.stopPropagation();else if (r = s.call(arguments), Y.set(this, i, r), t = o(this, i), this[i](), r !== (n = Y.get(this, i)) || t ? Y.set(this, i, !1) : n = {}, r !== n) return e.stopImmediatePropagation(), e.preventDefault(), n.value;
        } else r.length && (Y.set(this, i, {
          value: S.event.trigger(S.extend(r[0], S.Event.prototype), r.slice(1), this)
        }), e.stopImmediatePropagation());
      }
    })) : void 0 === Y.get(e, i) && S.event.add(e, i, Ce);
  }

  S.event = {
    global: {},
    add: function add(t, e, n, r, i) {
      var o,
          a,
          s,
          u,
          l,
          c,
          f,
          p,
          d,
          h,
          g,
          v = Y.get(t);

      if (V(t)) {
        n.handler && (n = (o = n).handler, i = o.selector), i && S.find.matchesSelector(re, i), n.guid || (n.guid = S.guid++), (u = v.events) || (u = v.events = Object.create(null)), (a = v.handle) || (a = v.handle = function (e) {
          return "undefined" != typeof S && S.event.triggered !== e.type ? S.event.dispatch.apply(t, arguments) : void 0;
        }), l = (e = (e || "").match(P) || [""]).length;

        while (l--) {
          d = g = (s = Te.exec(e[l]) || [])[1], h = (s[2] || "").split(".").sort(), d && (f = S.event.special[d] || {}, d = (i ? f.delegateType : f.bindType) || d, f = S.event.special[d] || {}, c = S.extend({
            type: d,
            origType: g,
            data: r,
            handler: n,
            guid: n.guid,
            selector: i,
            needsContext: i && S.expr.match.needsContext.test(i),
            namespace: h.join(".")
          }, o), (p = u[d]) || ((p = u[d] = []).delegateCount = 0, f.setup && !1 !== f.setup.call(t, r, h, a) || t.addEventListener && t.addEventListener(d, a)), f.add && (f.add.call(t, c), c.handler.guid || (c.handler.guid = n.guid)), i ? p.splice(p.delegateCount++, 0, c) : p.push(c), S.event.global[d] = !0);
        }
      }
    },
    remove: function remove(e, t, n, r, i) {
      var o,
          a,
          s,
          u,
          l,
          c,
          f,
          p,
          d,
          h,
          g,
          v = Y.hasData(e) && Y.get(e);

      if (v && (u = v.events)) {
        l = (t = (t || "").match(P) || [""]).length;

        while (l--) {
          if (d = g = (s = Te.exec(t[l]) || [])[1], h = (s[2] || "").split(".").sort(), d) {
            f = S.event.special[d] || {}, p = u[d = (r ? f.delegateType : f.bindType) || d] || [], s = s[2] && new RegExp("(^|\\.)" + h.join("\\.(?:.*\\.|)") + "(\\.|$)"), a = o = p.length;

            while (o--) {
              c = p[o], !i && g !== c.origType || n && n.guid !== c.guid || s && !s.test(c.namespace) || r && r !== c.selector && ("**" !== r || !c.selector) || (p.splice(o, 1), c.selector && p.delegateCount--, f.remove && f.remove.call(e, c));
            }

            a && !p.length && (f.teardown && !1 !== f.teardown.call(e, h, v.handle) || S.removeEvent(e, d, v.handle), delete u[d]);
          } else for (d in u) {
            S.event.remove(e, d + t[l], n, r, !0);
          }
        }

        S.isEmptyObject(u) && Y.remove(e, "handle events");
      }
    },
    dispatch: function dispatch(e) {
      var t,
          n,
          r,
          i,
          o,
          a,
          s = new Array(arguments.length),
          u = S.event.fix(e),
          l = (Y.get(this, "events") || Object.create(null))[u.type] || [],
          c = S.event.special[u.type] || {};

      for (s[0] = u, t = 1; t < arguments.length; t++) {
        s[t] = arguments[t];
      }

      if (u.delegateTarget = this, !c.preDispatch || !1 !== c.preDispatch.call(this, u)) {
        a = S.event.handlers.call(this, u, l), t = 0;

        while ((i = a[t++]) && !u.isPropagationStopped()) {
          u.currentTarget = i.elem, n = 0;

          while ((o = i.handlers[n++]) && !u.isImmediatePropagationStopped()) {
            u.rnamespace && !1 !== o.namespace && !u.rnamespace.test(o.namespace) || (u.handleObj = o, u.data = o.data, void 0 !== (r = ((S.event.special[o.origType] || {}).handle || o.handler).apply(i.elem, s)) && !1 === (u.result = r) && (u.preventDefault(), u.stopPropagation()));
          }
        }

        return c.postDispatch && c.postDispatch.call(this, u), u.result;
      }
    },
    handlers: function handlers(e, t) {
      var n,
          r,
          i,
          o,
          a,
          s = [],
          u = t.delegateCount,
          l = e.target;
      if (u && l.nodeType && !("click" === e.type && 1 <= e.button)) for (; l !== this; l = l.parentNode || this) {
        if (1 === l.nodeType && ("click" !== e.type || !0 !== l.disabled)) {
          for (o = [], a = {}, n = 0; n < u; n++) {
            void 0 === a[i = (r = t[n]).selector + " "] && (a[i] = r.needsContext ? -1 < S(i, this).index(l) : S.find(i, this, null, [l]).length), a[i] && o.push(r);
          }

          o.length && s.push({
            elem: l,
            handlers: o
          });
        }
      }
      return l = this, u < t.length && s.push({
        elem: l,
        handlers: t.slice(u)
      }), s;
    },
    addProp: function addProp(t, e) {
      Object.defineProperty(S.Event.prototype, t, {
        enumerable: !0,
        configurable: !0,
        get: m(e) ? function () {
          if (this.originalEvent) return e(this.originalEvent);
        } : function () {
          if (this.originalEvent) return this.originalEvent[t];
        },
        set: function set(e) {
          Object.defineProperty(this, t, {
            enumerable: !0,
            configurable: !0,
            writable: !0,
            value: e
          });
        }
      });
    },
    fix: function fix(e) {
      return e[S.expando] ? e : new S.Event(e);
    },
    special: {
      load: {
        noBubble: !0
      },
      click: {
        setup: function setup(e) {
          var t = this || e;
          return pe.test(t.type) && t.click && A(t, "input") && Ae(t, "click", Ce), !1;
        },
        trigger: function trigger(e) {
          var t = this || e;
          return pe.test(t.type) && t.click && A(t, "input") && Ae(t, "click"), !0;
        },
        _default: function _default(e) {
          var t = e.target;
          return pe.test(t.type) && t.click && A(t, "input") && Y.get(t, "click") || A(t, "a");
        }
      },
      beforeunload: {
        postDispatch: function postDispatch(e) {
          void 0 !== e.result && e.originalEvent && (e.originalEvent.returnValue = e.result);
        }
      }
    }
  }, S.removeEvent = function (e, t, n) {
    e.removeEventListener && e.removeEventListener(t, n);
  }, S.Event = function (e, t) {
    if (!(this instanceof S.Event)) return new S.Event(e, t);
    e && e.type ? (this.originalEvent = e, this.type = e.type, this.isDefaultPrevented = e.defaultPrevented || void 0 === e.defaultPrevented && !1 === e.returnValue ? Ce : Ee, this.target = e.target && 3 === e.target.nodeType ? e.target.parentNode : e.target, this.currentTarget = e.currentTarget, this.relatedTarget = e.relatedTarget) : this.type = e, t && S.extend(this, t), this.timeStamp = e && e.timeStamp || Date.now(), this[S.expando] = !0;
  }, S.Event.prototype = {
    constructor: S.Event,
    isDefaultPrevented: Ee,
    isPropagationStopped: Ee,
    isImmediatePropagationStopped: Ee,
    isSimulated: !1,
    preventDefault: function preventDefault() {
      var e = this.originalEvent;
      this.isDefaultPrevented = Ce, e && !this.isSimulated && e.preventDefault();
    },
    stopPropagation: function stopPropagation() {
      var e = this.originalEvent;
      this.isPropagationStopped = Ce, e && !this.isSimulated && e.stopPropagation();
    },
    stopImmediatePropagation: function stopImmediatePropagation() {
      var e = this.originalEvent;
      this.isImmediatePropagationStopped = Ce, e && !this.isSimulated && e.stopImmediatePropagation(), this.stopPropagation();
    }
  }, S.each({
    altKey: !0,
    bubbles: !0,
    cancelable: !0,
    changedTouches: !0,
    ctrlKey: !0,
    detail: !0,
    eventPhase: !0,
    metaKey: !0,
    pageX: !0,
    pageY: !0,
    shiftKey: !0,
    view: !0,
    "char": !0,
    code: !0,
    charCode: !0,
    key: !0,
    keyCode: !0,
    button: !0,
    buttons: !0,
    clientX: !0,
    clientY: !0,
    offsetX: !0,
    offsetY: !0,
    pointerId: !0,
    pointerType: !0,
    screenX: !0,
    screenY: !0,
    targetTouches: !0,
    toElement: !0,
    touches: !0,
    which: function which(e) {
      var t = e.button;
      return null == e.which && be.test(e.type) ? null != e.charCode ? e.charCode : e.keyCode : !e.which && void 0 !== t && we.test(e.type) ? 1 & t ? 1 : 2 & t ? 3 : 4 & t ? 2 : 0 : e.which;
    }
  }, S.event.addProp), S.each({
    focus: "focusin",
    blur: "focusout"
  }, function (e, t) {
    S.event.special[e] = {
      setup: function setup() {
        return Ae(this, e, Se), !1;
      },
      trigger: function trigger() {
        return Ae(this, e), !0;
      },
      delegateType: t
    };
  }), S.each({
    mouseenter: "mouseover",
    mouseleave: "mouseout",
    pointerenter: "pointerover",
    pointerleave: "pointerout"
  }, function (e, i) {
    S.event.special[e] = {
      delegateType: i,
      bindType: i,
      handle: function handle(e) {
        var t,
            n = e.relatedTarget,
            r = e.handleObj;
        return n && (n === this || S.contains(this, n)) || (e.type = r.origType, t = r.handler.apply(this, arguments), e.type = i), t;
      }
    };
  }), S.fn.extend({
    on: function on(e, t, n, r) {
      return ke(this, e, t, n, r);
    },
    one: function one(e, t, n, r) {
      return ke(this, e, t, n, r, 1);
    },
    off: function off(e, t, n) {
      var r, i;
      if (e && e.preventDefault && e.handleObj) return r = e.handleObj, S(e.delegateTarget).off(r.namespace ? r.origType + "." + r.namespace : r.origType, r.selector, r.handler), this;

      if ("object" == _typeof(e)) {
        for (i in e) {
          this.off(i, t, e[i]);
        }

        return this;
      }

      return !1 !== t && "function" != typeof t || (n = t, t = void 0), !1 === n && (n = Ee), this.each(function () {
        S.event.remove(this, e, n, t);
      });
    }
  });
  var Ne = /<script|<style|<link/i,
      De = /checked\s*(?:[^=]|=\s*.checked.)/i,
      je = /^\s*<!(?:\[CDATA\[|--)|(?:\]\]|--)>\s*$/g;

  function qe(e, t) {
    return A(e, "table") && A(11 !== t.nodeType ? t : t.firstChild, "tr") && S(e).children("tbody")[0] || e;
  }

  function Le(e) {
    return e.type = (null !== e.getAttribute("type")) + "/" + e.type, e;
  }

  function He(e) {
    return "true/" === (e.type || "").slice(0, 5) ? e.type = e.type.slice(5) : e.removeAttribute("type"), e;
  }

  function Oe(e, t) {
    var n, r, i, o, a, s;

    if (1 === t.nodeType) {
      if (Y.hasData(e) && (s = Y.get(e).events)) for (i in Y.remove(t, "handle events"), s) {
        for (n = 0, r = s[i].length; n < r; n++) {
          S.event.add(t, i, s[i][n]);
        }
      }
      Q.hasData(e) && (o = Q.access(e), a = S.extend({}, o), Q.set(t, a));
    }
  }

  function Pe(n, r, i, o) {
    r = g(r);
    var e,
        t,
        a,
        s,
        u,
        l,
        c = 0,
        f = n.length,
        p = f - 1,
        d = r[0],
        h = m(d);
    if (h || 1 < f && "string" == typeof d && !y.checkClone && De.test(d)) return n.each(function (e) {
      var t = n.eq(e);
      h && (r[0] = d.call(this, e, t.html())), Pe(t, r, i, o);
    });

    if (f && (t = (e = xe(r, n[0].ownerDocument, !1, n, o)).firstChild, 1 === e.childNodes.length && (e = t), t || o)) {
      for (s = (a = S.map(ve(e, "script"), Le)).length; c < f; c++) {
        u = e, c !== p && (u = S.clone(u, !0, !0), s && S.merge(a, ve(u, "script"))), i.call(n[c], u, c);
      }

      if (s) for (l = a[a.length - 1].ownerDocument, S.map(a, He), c = 0; c < s; c++) {
        u = a[c], he.test(u.type || "") && !Y.access(u, "globalEval") && S.contains(l, u) && (u.src && "module" !== (u.type || "").toLowerCase() ? S._evalUrl && !u.noModule && S._evalUrl(u.src, {
          nonce: u.nonce || u.getAttribute("nonce")
        }, l) : b(u.textContent.replace(je, ""), u, l));
      }
    }

    return n;
  }

  function Re(e, t, n) {
    for (var r, i = t ? S.filter(t, e) : e, o = 0; null != (r = i[o]); o++) {
      n || 1 !== r.nodeType || S.cleanData(ve(r)), r.parentNode && (n && ie(r) && ye(ve(r, "script")), r.parentNode.removeChild(r));
    }

    return e;
  }

  S.extend({
    htmlPrefilter: function htmlPrefilter(e) {
      return e;
    },
    clone: function clone(e, t, n) {
      var r,
          i,
          o,
          a,
          s,
          u,
          l,
          c = e.cloneNode(!0),
          f = ie(e);
      if (!(y.noCloneChecked || 1 !== e.nodeType && 11 !== e.nodeType || S.isXMLDoc(e))) for (a = ve(c), r = 0, i = (o = ve(e)).length; r < i; r++) {
        s = o[r], u = a[r], void 0, "input" === (l = u.nodeName.toLowerCase()) && pe.test(s.type) ? u.checked = s.checked : "input" !== l && "textarea" !== l || (u.defaultValue = s.defaultValue);
      }
      if (t) if (n) for (o = o || ve(e), a = a || ve(c), r = 0, i = o.length; r < i; r++) {
        Oe(o[r], a[r]);
      } else Oe(e, c);
      return 0 < (a = ve(c, "script")).length && ye(a, !f && ve(e, "script")), c;
    },
    cleanData: function cleanData(e) {
      for (var t, n, r, i = S.event.special, o = 0; void 0 !== (n = e[o]); o++) {
        if (V(n)) {
          if (t = n[Y.expando]) {
            if (t.events) for (r in t.events) {
              i[r] ? S.event.remove(n, r) : S.removeEvent(n, r, t.handle);
            }
            n[Y.expando] = void 0;
          }

          n[Q.expando] && (n[Q.expando] = void 0);
        }
      }
    }
  }), S.fn.extend({
    detach: function detach(e) {
      return Re(this, e, !0);
    },
    remove: function remove(e) {
      return Re(this, e);
    },
    text: function text(e) {
      return $(this, function (e) {
        return void 0 === e ? S.text(this) : this.empty().each(function () {
          1 !== this.nodeType && 11 !== this.nodeType && 9 !== this.nodeType || (this.textContent = e);
        });
      }, null, e, arguments.length);
    },
    append: function append() {
      return Pe(this, arguments, function (e) {
        1 !== this.nodeType && 11 !== this.nodeType && 9 !== this.nodeType || qe(this, e).appendChild(e);
      });
    },
    prepend: function prepend() {
      return Pe(this, arguments, function (e) {
        if (1 === this.nodeType || 11 === this.nodeType || 9 === this.nodeType) {
          var t = qe(this, e);
          t.insertBefore(e, t.firstChild);
        }
      });
    },
    before: function before() {
      return Pe(this, arguments, function (e) {
        this.parentNode && this.parentNode.insertBefore(e, this);
      });
    },
    after: function after() {
      return Pe(this, arguments, function (e) {
        this.parentNode && this.parentNode.insertBefore(e, this.nextSibling);
      });
    },
    empty: function empty() {
      for (var e, t = 0; null != (e = this[t]); t++) {
        1 === e.nodeType && (S.cleanData(ve(e, !1)), e.textContent = "");
      }

      return this;
    },
    clone: function clone(e, t) {
      return e = null != e && e, t = null == t ? e : t, this.map(function () {
        return S.clone(this, e, t);
      });
    },
    html: function html(e) {
      return $(this, function (e) {
        var t = this[0] || {},
            n = 0,
            r = this.length;
        if (void 0 === e && 1 === t.nodeType) return t.innerHTML;

        if ("string" == typeof e && !Ne.test(e) && !ge[(de.exec(e) || ["", ""])[1].toLowerCase()]) {
          e = S.htmlPrefilter(e);

          try {
            for (; n < r; n++) {
              1 === (t = this[n] || {}).nodeType && (S.cleanData(ve(t, !1)), t.innerHTML = e);
            }

            t = 0;
          } catch (e) {}
        }

        t && this.empty().append(e);
      }, null, e, arguments.length);
    },
    replaceWith: function replaceWith() {
      var n = [];
      return Pe(this, arguments, function (e) {
        var t = this.parentNode;
        S.inArray(this, n) < 0 && (S.cleanData(ve(this)), t && t.replaceChild(e, this));
      }, n);
    }
  }), S.each({
    appendTo: "append",
    prependTo: "prepend",
    insertBefore: "before",
    insertAfter: "after",
    replaceAll: "replaceWith"
  }, function (e, a) {
    S.fn[e] = function (e) {
      for (var t, n = [], r = S(e), i = r.length - 1, o = 0; o <= i; o++) {
        t = o === i ? this : this.clone(!0), S(r[o])[a](t), u.apply(n, t.get());
      }

      return this.pushStack(n);
    };
  });

  var Me = new RegExp("^(" + ee + ")(?!px)[a-z%]+$", "i"),
      Ie = function Ie(e) {
    var t = e.ownerDocument.defaultView;
    return t && t.opener || (t = C), t.getComputedStyle(e);
  },
      We = function We(e, t, n) {
    var r,
        i,
        o = {};

    for (i in t) {
      o[i] = e.style[i], e.style[i] = t[i];
    }

    for (i in r = n.call(e), t) {
      e.style[i] = o[i];
    }

    return r;
  },
      Fe = new RegExp(ne.join("|"), "i");

  function Be(e, t, n) {
    var r,
        i,
        o,
        a,
        s = e.style;
    return (n = n || Ie(e)) && ("" !== (a = n.getPropertyValue(t) || n[t]) || ie(e) || (a = S.style(e, t)), !y.pixelBoxStyles() && Me.test(a) && Fe.test(t) && (r = s.width, i = s.minWidth, o = s.maxWidth, s.minWidth = s.maxWidth = s.width = a, a = n.width, s.width = r, s.minWidth = i, s.maxWidth = o)), void 0 !== a ? a + "" : a;
  }

  function $e(e, t) {
    return {
      get: function get() {
        if (!e()) return (this.get = t).apply(this, arguments);
        delete this.get;
      }
    };
  }

  !function () {
    function e() {
      if (l) {
        u.style.cssText = "position:absolute;left:-11111px;width:60px;margin-top:1px;padding:0;border:0", l.style.cssText = "position:relative;display:block;box-sizing:border-box;overflow:scroll;margin:auto;border:1px;padding:1px;width:60%;top:1%", re.appendChild(u).appendChild(l);
        var e = C.getComputedStyle(l);
        n = "1%" !== e.top, s = 12 === t(e.marginLeft), l.style.right = "60%", o = 36 === t(e.right), r = 36 === t(e.width), l.style.position = "absolute", i = 12 === t(l.offsetWidth / 3), re.removeChild(u), l = null;
      }
    }

    function t(e) {
      return Math.round(parseFloat(e));
    }

    var n,
        r,
        i,
        o,
        a,
        s,
        u = E.createElement("div"),
        l = E.createElement("div");
    l.style && (l.style.backgroundClip = "content-box", l.cloneNode(!0).style.backgroundClip = "", y.clearCloneStyle = "content-box" === l.style.backgroundClip, S.extend(y, {
      boxSizingReliable: function boxSizingReliable() {
        return e(), r;
      },
      pixelBoxStyles: function pixelBoxStyles() {
        return e(), o;
      },
      pixelPosition: function pixelPosition() {
        return e(), n;
      },
      reliableMarginLeft: function reliableMarginLeft() {
        return e(), s;
      },
      scrollboxSize: function scrollboxSize() {
        return e(), i;
      },
      reliableTrDimensions: function reliableTrDimensions() {
        var e, t, n, r;
        return null == a && (e = E.createElement("table"), t = E.createElement("tr"), n = E.createElement("div"), e.style.cssText = "position:absolute;left:-11111px", t.style.height = "1px", n.style.height = "9px", re.appendChild(e).appendChild(t).appendChild(n), r = C.getComputedStyle(t), a = 3 < parseInt(r.height), re.removeChild(e)), a;
      }
    }));
  }();
  var _e = ["Webkit", "Moz", "ms"],
      ze = E.createElement("div").style,
      Ue = {};

  function Xe(e) {
    var t = S.cssProps[e] || Ue[e];
    return t || (e in ze ? e : Ue[e] = function (e) {
      var t = e[0].toUpperCase() + e.slice(1),
          n = _e.length;

      while (n--) {
        if ((e = _e[n] + t) in ze) return e;
      }
    }(e) || e);
  }

  var Ve = /^(none|table(?!-c[ea]).+)/,
      Ge = /^--/,
      Ye = {
    position: "absolute",
    visibility: "hidden",
    display: "block"
  },
      Qe = {
    letterSpacing: "0",
    fontWeight: "400"
  };

  function Je(e, t, n) {
    var r = te.exec(t);
    return r ? Math.max(0, r[2] - (n || 0)) + (r[3] || "px") : t;
  }

  function Ke(e, t, n, r, i, o) {
    var a = "width" === t ? 1 : 0,
        s = 0,
        u = 0;
    if (n === (r ? "border" : "content")) return 0;

    for (; a < 4; a += 2) {
      "margin" === n && (u += S.css(e, n + ne[a], !0, i)), r ? ("content" === n && (u -= S.css(e, "padding" + ne[a], !0, i)), "margin" !== n && (u -= S.css(e, "border" + ne[a] + "Width", !0, i))) : (u += S.css(e, "padding" + ne[a], !0, i), "padding" !== n ? u += S.css(e, "border" + ne[a] + "Width", !0, i) : s += S.css(e, "border" + ne[a] + "Width", !0, i));
    }

    return !r && 0 <= o && (u += Math.max(0, Math.ceil(e["offset" + t[0].toUpperCase() + t.slice(1)] - o - u - s - .5)) || 0), u;
  }

  function Ze(e, t, n) {
    var r = Ie(e),
        i = (!y.boxSizingReliable() || n) && "border-box" === S.css(e, "boxSizing", !1, r),
        o = i,
        a = Be(e, t, r),
        s = "offset" + t[0].toUpperCase() + t.slice(1);

    if (Me.test(a)) {
      if (!n) return a;
      a = "auto";
    }

    return (!y.boxSizingReliable() && i || !y.reliableTrDimensions() && A(e, "tr") || "auto" === a || !parseFloat(a) && "inline" === S.css(e, "display", !1, r)) && e.getClientRects().length && (i = "border-box" === S.css(e, "boxSizing", !1, r), (o = s in e) && (a = e[s])), (a = parseFloat(a) || 0) + Ke(e, t, n || (i ? "border" : "content"), o, r, a) + "px";
  }

  function et(e, t, n, r, i) {
    return new et.prototype.init(e, t, n, r, i);
  }

  S.extend({
    cssHooks: {
      opacity: {
        get: function get(e, t) {
          if (t) {
            var n = Be(e, "opacity");
            return "" === n ? "1" : n;
          }
        }
      }
    },
    cssNumber: {
      animationIterationCount: !0,
      columnCount: !0,
      fillOpacity: !0,
      flexGrow: !0,
      flexShrink: !0,
      fontWeight: !0,
      gridArea: !0,
      gridColumn: !0,
      gridColumnEnd: !0,
      gridColumnStart: !0,
      gridRow: !0,
      gridRowEnd: !0,
      gridRowStart: !0,
      lineHeight: !0,
      opacity: !0,
      order: !0,
      orphans: !0,
      widows: !0,
      zIndex: !0,
      zoom: !0
    },
    cssProps: {},
    style: function style(e, t, n, r) {
      if (e && 3 !== e.nodeType && 8 !== e.nodeType && e.style) {
        var i,
            o,
            a,
            s = X(t),
            u = Ge.test(t),
            l = e.style;
        if (u || (t = Xe(s)), a = S.cssHooks[t] || S.cssHooks[s], void 0 === n) return a && "get" in a && void 0 !== (i = a.get(e, !1, r)) ? i : l[t];
        "string" === (o = _typeof(n)) && (i = te.exec(n)) && i[1] && (n = se(e, t, i), o = "number"), null != n && n == n && ("number" !== o || u || (n += i && i[3] || (S.cssNumber[s] ? "" : "px")), y.clearCloneStyle || "" !== n || 0 !== t.indexOf("background") || (l[t] = "inherit"), a && "set" in a && void 0 === (n = a.set(e, n, r)) || (u ? l.setProperty(t, n) : l[t] = n));
      }
    },
    css: function css(e, t, n, r) {
      var i,
          o,
          a,
          s = X(t);
      return Ge.test(t) || (t = Xe(s)), (a = S.cssHooks[t] || S.cssHooks[s]) && "get" in a && (i = a.get(e, !0, n)), void 0 === i && (i = Be(e, t, r)), "normal" === i && t in Qe && (i = Qe[t]), "" === n || n ? (o = parseFloat(i), !0 === n || isFinite(o) ? o || 0 : i) : i;
    }
  }), S.each(["height", "width"], function (e, u) {
    S.cssHooks[u] = {
      get: function get(e, t, n) {
        if (t) return !Ve.test(S.css(e, "display")) || e.getClientRects().length && e.getBoundingClientRect().width ? Ze(e, u, n) : We(e, Ye, function () {
          return Ze(e, u, n);
        });
      },
      set: function set(e, t, n) {
        var r,
            i = Ie(e),
            o = !y.scrollboxSize() && "absolute" === i.position,
            a = (o || n) && "border-box" === S.css(e, "boxSizing", !1, i),
            s = n ? Ke(e, u, n, a, i) : 0;
        return a && o && (s -= Math.ceil(e["offset" + u[0].toUpperCase() + u.slice(1)] - parseFloat(i[u]) - Ke(e, u, "border", !1, i) - .5)), s && (r = te.exec(t)) && "px" !== (r[3] || "px") && (e.style[u] = t, t = S.css(e, u)), Je(0, t, s);
      }
    };
  }), S.cssHooks.marginLeft = $e(y.reliableMarginLeft, function (e, t) {
    if (t) return (parseFloat(Be(e, "marginLeft")) || e.getBoundingClientRect().left - We(e, {
      marginLeft: 0
    }, function () {
      return e.getBoundingClientRect().left;
    })) + "px";
  }), S.each({
    margin: "",
    padding: "",
    border: "Width"
  }, function (i, o) {
    S.cssHooks[i + o] = {
      expand: function expand(e) {
        for (var t = 0, n = {}, r = "string" == typeof e ? e.split(" ") : [e]; t < 4; t++) {
          n[i + ne[t] + o] = r[t] || r[t - 2] || r[0];
        }

        return n;
      }
    }, "margin" !== i && (S.cssHooks[i + o].set = Je);
  }), S.fn.extend({
    css: function css(e, t) {
      return $(this, function (e, t, n) {
        var r,
            i,
            o = {},
            a = 0;

        if (Array.isArray(t)) {
          for (r = Ie(e), i = t.length; a < i; a++) {
            o[t[a]] = S.css(e, t[a], !1, r);
          }

          return o;
        }

        return void 0 !== n ? S.style(e, t, n) : S.css(e, t);
      }, e, t, 1 < arguments.length);
    }
  }), ((S.Tween = et).prototype = {
    constructor: et,
    init: function init(e, t, n, r, i, o) {
      this.elem = e, this.prop = n, this.easing = i || S.easing._default, this.options = t, this.start = this.now = this.cur(), this.end = r, this.unit = o || (S.cssNumber[n] ? "" : "px");
    },
    cur: function cur() {
      var e = et.propHooks[this.prop];
      return e && e.get ? e.get(this) : et.propHooks._default.get(this);
    },
    run: function run(e) {
      var t,
          n = et.propHooks[this.prop];
      return this.options.duration ? this.pos = t = S.easing[this.easing](e, this.options.duration * e, 0, 1, this.options.duration) : this.pos = t = e, this.now = (this.end - this.start) * t + this.start, this.options.step && this.options.step.call(this.elem, this.now, this), n && n.set ? n.set(this) : et.propHooks._default.set(this), this;
    }
  }).init.prototype = et.prototype, (et.propHooks = {
    _default: {
      get: function get(e) {
        var t;
        return 1 !== e.elem.nodeType || null != e.elem[e.prop] && null == e.elem.style[e.prop] ? e.elem[e.prop] : (t = S.css(e.elem, e.prop, "")) && "auto" !== t ? t : 0;
      },
      set: function set(e) {
        S.fx.step[e.prop] ? S.fx.step[e.prop](e) : 1 !== e.elem.nodeType || !S.cssHooks[e.prop] && null == e.elem.style[Xe(e.prop)] ? e.elem[e.prop] = e.now : S.style(e.elem, e.prop, e.now + e.unit);
      }
    }
  }).scrollTop = et.propHooks.scrollLeft = {
    set: function set(e) {
      e.elem.nodeType && e.elem.parentNode && (e.elem[e.prop] = e.now);
    }
  }, S.easing = {
    linear: function linear(e) {
      return e;
    },
    swing: function swing(e) {
      return .5 - Math.cos(e * Math.PI) / 2;
    },
    _default: "swing"
  }, S.fx = et.prototype.init, S.fx.step = {};
  var tt,
      nt,
      rt,
      it,
      ot = /^(?:toggle|show|hide)$/,
      at = /queueHooks$/;

  function st() {
    nt && (!1 === E.hidden && C.requestAnimationFrame ? C.requestAnimationFrame(st) : C.setTimeout(st, S.fx.interval), S.fx.tick());
  }

  function ut() {
    return C.setTimeout(function () {
      tt = void 0;
    }), tt = Date.now();
  }

  function lt(e, t) {
    var n,
        r = 0,
        i = {
      height: e
    };

    for (t = t ? 1 : 0; r < 4; r += 2 - t) {
      i["margin" + (n = ne[r])] = i["padding" + n] = e;
    }

    return t && (i.opacity = i.width = e), i;
  }

  function ct(e, t, n) {
    for (var r, i = (ft.tweeners[t] || []).concat(ft.tweeners["*"]), o = 0, a = i.length; o < a; o++) {
      if (r = i[o].call(n, t, e)) return r;
    }
  }

  function ft(o, e, t) {
    var n,
        a,
        r = 0,
        i = ft.prefilters.length,
        s = S.Deferred().always(function () {
      delete u.elem;
    }),
        u = function u() {
      if (a) return !1;

      for (var e = tt || ut(), t = Math.max(0, l.startTime + l.duration - e), n = 1 - (t / l.duration || 0), r = 0, i = l.tweens.length; r < i; r++) {
        l.tweens[r].run(n);
      }

      return s.notifyWith(o, [l, n, t]), n < 1 && i ? t : (i || s.notifyWith(o, [l, 1, 0]), s.resolveWith(o, [l]), !1);
    },
        l = s.promise({
      elem: o,
      props: S.extend({}, e),
      opts: S.extend(!0, {
        specialEasing: {},
        easing: S.easing._default
      }, t),
      originalProperties: e,
      originalOptions: t,
      startTime: tt || ut(),
      duration: t.duration,
      tweens: [],
      createTween: function createTween(e, t) {
        var n = S.Tween(o, l.opts, e, t, l.opts.specialEasing[e] || l.opts.easing);
        return l.tweens.push(n), n;
      },
      stop: function stop(e) {
        var t = 0,
            n = e ? l.tweens.length : 0;
        if (a) return this;

        for (a = !0; t < n; t++) {
          l.tweens[t].run(1);
        }

        return e ? (s.notifyWith(o, [l, 1, 0]), s.resolveWith(o, [l, e])) : s.rejectWith(o, [l, e]), this;
      }
    }),
        c = l.props;

    for (!function (e, t) {
      var n, r, i, o, a;

      for (n in e) {
        if (i = t[r = X(n)], o = e[n], Array.isArray(o) && (i = o[1], o = e[n] = o[0]), n !== r && (e[r] = o, delete e[n]), (a = S.cssHooks[r]) && ("expand" in a)) for (n in o = a.expand(o), delete e[r], o) {
          (n in e) || (e[n] = o[n], t[n] = i);
        } else t[r] = i;
      }
    }(c, l.opts.specialEasing); r < i; r++) {
      if (n = ft.prefilters[r].call(l, o, c, l.opts)) return m(n.stop) && (S._queueHooks(l.elem, l.opts.queue).stop = n.stop.bind(n)), n;
    }

    return S.map(c, ct, l), m(l.opts.start) && l.opts.start.call(o, l), l.progress(l.opts.progress).done(l.opts.done, l.opts.complete).fail(l.opts.fail).always(l.opts.always), S.fx.timer(S.extend(u, {
      elem: o,
      anim: l,
      queue: l.opts.queue
    })), l;
  }

  S.Animation = S.extend(ft, {
    tweeners: {
      "*": [function (e, t) {
        var n = this.createTween(e, t);
        return se(n.elem, e, te.exec(t), n), n;
      }]
    },
    tweener: function tweener(e, t) {
      m(e) ? (t = e, e = ["*"]) : e = e.match(P);

      for (var n, r = 0, i = e.length; r < i; r++) {
        n = e[r], ft.tweeners[n] = ft.tweeners[n] || [], ft.tweeners[n].unshift(t);
      }
    },
    prefilters: [function (e, t, n) {
      var r,
          i,
          o,
          a,
          s,
          u,
          l,
          c,
          f = "width" in t || "height" in t,
          p = this,
          d = {},
          h = e.style,
          g = e.nodeType && ae(e),
          v = Y.get(e, "fxshow");

      for (r in n.queue || (null == (a = S._queueHooks(e, "fx")).unqueued && (a.unqueued = 0, s = a.empty.fire, a.empty.fire = function () {
        a.unqueued || s();
      }), a.unqueued++, p.always(function () {
        p.always(function () {
          a.unqueued--, S.queue(e, "fx").length || a.empty.fire();
        });
      })), t) {
        if (i = t[r], ot.test(i)) {
          if (delete t[r], o = o || "toggle" === i, i === (g ? "hide" : "show")) {
            if ("show" !== i || !v || void 0 === v[r]) continue;
            g = !0;
          }

          d[r] = v && v[r] || S.style(e, r);
        }
      }

      if ((u = !S.isEmptyObject(t)) || !S.isEmptyObject(d)) for (r in f && 1 === e.nodeType && (n.overflow = [h.overflow, h.overflowX, h.overflowY], null == (l = v && v.display) && (l = Y.get(e, "display")), "none" === (c = S.css(e, "display")) && (l ? c = l : (le([e], !0), l = e.style.display || l, c = S.css(e, "display"), le([e]))), ("inline" === c || "inline-block" === c && null != l) && "none" === S.css(e, "float") && (u || (p.done(function () {
        h.display = l;
      }), null == l && (c = h.display, l = "none" === c ? "" : c)), h.display = "inline-block")), n.overflow && (h.overflow = "hidden", p.always(function () {
        h.overflow = n.overflow[0], h.overflowX = n.overflow[1], h.overflowY = n.overflow[2];
      })), u = !1, d) {
        u || (v ? "hidden" in v && (g = v.hidden) : v = Y.access(e, "fxshow", {
          display: l
        }), o && (v.hidden = !g), g && le([e], !0), p.done(function () {
          for (r in g || le([e]), Y.remove(e, "fxshow"), d) {
            S.style(e, r, d[r]);
          }
        })), u = ct(g ? v[r] : 0, r, p), r in v || (v[r] = u.start, g && (u.end = u.start, u.start = 0));
      }
    }],
    prefilter: function prefilter(e, t) {
      t ? ft.prefilters.unshift(e) : ft.prefilters.push(e);
    }
  }), S.speed = function (e, t, n) {
    var r = e && "object" == _typeof(e) ? S.extend({}, e) : {
      complete: n || !n && t || m(e) && e,
      duration: e,
      easing: n && t || t && !m(t) && t
    };
    return S.fx.off ? r.duration = 0 : "number" != typeof r.duration && (r.duration in S.fx.speeds ? r.duration = S.fx.speeds[r.duration] : r.duration = S.fx.speeds._default), null != r.queue && !0 !== r.queue || (r.queue = "fx"), r.old = r.complete, r.complete = function () {
      m(r.old) && r.old.call(this), r.queue && S.dequeue(this, r.queue);
    }, r;
  }, S.fn.extend({
    fadeTo: function fadeTo(e, t, n, r) {
      return this.filter(ae).css("opacity", 0).show().end().animate({
        opacity: t
      }, e, n, r);
    },
    animate: function animate(t, e, n, r) {
      var i = S.isEmptyObject(t),
          o = S.speed(e, n, r),
          a = function a() {
        var e = ft(this, S.extend({}, t), o);
        (i || Y.get(this, "finish")) && e.stop(!0);
      };

      return a.finish = a, i || !1 === o.queue ? this.each(a) : this.queue(o.queue, a);
    },
    stop: function stop(i, e, o) {
      var a = function a(e) {
        var t = e.stop;
        delete e.stop, t(o);
      };

      return "string" != typeof i && (o = e, e = i, i = void 0), e && this.queue(i || "fx", []), this.each(function () {
        var e = !0,
            t = null != i && i + "queueHooks",
            n = S.timers,
            r = Y.get(this);
        if (t) r[t] && r[t].stop && a(r[t]);else for (t in r) {
          r[t] && r[t].stop && at.test(t) && a(r[t]);
        }

        for (t = n.length; t--;) {
          n[t].elem !== this || null != i && n[t].queue !== i || (n[t].anim.stop(o), e = !1, n.splice(t, 1));
        }

        !e && o || S.dequeue(this, i);
      });
    },
    finish: function finish(a) {
      return !1 !== a && (a = a || "fx"), this.each(function () {
        var e,
            t = Y.get(this),
            n = t[a + "queue"],
            r = t[a + "queueHooks"],
            i = S.timers,
            o = n ? n.length : 0;

        for (t.finish = !0, S.queue(this, a, []), r && r.stop && r.stop.call(this, !0), e = i.length; e--;) {
          i[e].elem === this && i[e].queue === a && (i[e].anim.stop(!0), i.splice(e, 1));
        }

        for (e = 0; e < o; e++) {
          n[e] && n[e].finish && n[e].finish.call(this);
        }

        delete t.finish;
      });
    }
  }), S.each(["toggle", "show", "hide"], function (e, r) {
    var i = S.fn[r];

    S.fn[r] = function (e, t, n) {
      return null == e || "boolean" == typeof e ? i.apply(this, arguments) : this.animate(lt(r, !0), e, t, n);
    };
  }), S.each({
    slideDown: lt("show"),
    slideUp: lt("hide"),
    slideToggle: lt("toggle"),
    fadeIn: {
      opacity: "show"
    },
    fadeOut: {
      opacity: "hide"
    },
    fadeToggle: {
      opacity: "toggle"
    }
  }, function (e, r) {
    S.fn[e] = function (e, t, n) {
      return this.animate(r, e, t, n);
    };
  }), S.timers = [], S.fx.tick = function () {
    var e,
        t = 0,
        n = S.timers;

    for (tt = Date.now(); t < n.length; t++) {
      (e = n[t])() || n[t] !== e || n.splice(t--, 1);
    }

    n.length || S.fx.stop(), tt = void 0;
  }, S.fx.timer = function (e) {
    S.timers.push(e), S.fx.start();
  }, S.fx.interval = 13, S.fx.start = function () {
    nt || (nt = !0, st());
  }, S.fx.stop = function () {
    nt = null;
  }, S.fx.speeds = {
    slow: 600,
    fast: 200,
    _default: 400
  }, S.fn.delay = function (r, e) {
    return r = S.fx && S.fx.speeds[r] || r, e = e || "fx", this.queue(e, function (e, t) {
      var n = C.setTimeout(e, r);

      t.stop = function () {
        C.clearTimeout(n);
      };
    });
  }, rt = E.createElement("input"), it = E.createElement("select").appendChild(E.createElement("option")), rt.type = "checkbox", y.checkOn = "" !== rt.value, y.optSelected = it.selected, (rt = E.createElement("input")).value = "t", rt.type = "radio", y.radioValue = "t" === rt.value;
  var pt,
      dt = S.expr.attrHandle;
  S.fn.extend({
    attr: function attr(e, t) {
      return $(this, S.attr, e, t, 1 < arguments.length);
    },
    removeAttr: function removeAttr(e) {
      return this.each(function () {
        S.removeAttr(this, e);
      });
    }
  }), S.extend({
    attr: function attr(e, t, n) {
      var r,
          i,
          o = e.nodeType;
      if (3 !== o && 8 !== o && 2 !== o) return "undefined" == typeof e.getAttribute ? S.prop(e, t, n) : (1 === o && S.isXMLDoc(e) || (i = S.attrHooks[t.toLowerCase()] || (S.expr.match.bool.test(t) ? pt : void 0)), void 0 !== n ? null === n ? void S.removeAttr(e, t) : i && "set" in i && void 0 !== (r = i.set(e, n, t)) ? r : (e.setAttribute(t, n + ""), n) : i && "get" in i && null !== (r = i.get(e, t)) ? r : null == (r = S.find.attr(e, t)) ? void 0 : r);
    },
    attrHooks: {
      type: {
        set: function set(e, t) {
          if (!y.radioValue && "radio" === t && A(e, "input")) {
            var n = e.value;
            return e.setAttribute("type", t), n && (e.value = n), t;
          }
        }
      }
    },
    removeAttr: function removeAttr(e, t) {
      var n,
          r = 0,
          i = t && t.match(P);
      if (i && 1 === e.nodeType) while (n = i[r++]) {
        e.removeAttribute(n);
      }
    }
  }), pt = {
    set: function set(e, t, n) {
      return !1 === t ? S.removeAttr(e, n) : e.setAttribute(n, n), n;
    }
  }, S.each(S.expr.match.bool.source.match(/\w+/g), function (e, t) {
    var a = dt[t] || S.find.attr;

    dt[t] = function (e, t, n) {
      var r,
          i,
          o = t.toLowerCase();
      return n || (i = dt[o], dt[o] = r, r = null != a(e, t, n) ? o : null, dt[o] = i), r;
    };
  });
  var ht = /^(?:input|select|textarea|button)$/i,
      gt = /^(?:a|area)$/i;

  function vt(e) {
    return (e.match(P) || []).join(" ");
  }

  function yt(e) {
    return e.getAttribute && e.getAttribute("class") || "";
  }

  function mt(e) {
    return Array.isArray(e) ? e : "string" == typeof e && e.match(P) || [];
  }

  S.fn.extend({
    prop: function prop(e, t) {
      return $(this, S.prop, e, t, 1 < arguments.length);
    },
    removeProp: function removeProp(e) {
      return this.each(function () {
        delete this[S.propFix[e] || e];
      });
    }
  }), S.extend({
    prop: function prop(e, t, n) {
      var r,
          i,
          o = e.nodeType;
      if (3 !== o && 8 !== o && 2 !== o) return 1 === o && S.isXMLDoc(e) || (t = S.propFix[t] || t, i = S.propHooks[t]), void 0 !== n ? i && "set" in i && void 0 !== (r = i.set(e, n, t)) ? r : e[t] = n : i && "get" in i && null !== (r = i.get(e, t)) ? r : e[t];
    },
    propHooks: {
      tabIndex: {
        get: function get(e) {
          var t = S.find.attr(e, "tabindex");
          return t ? parseInt(t, 10) : ht.test(e.nodeName) || gt.test(e.nodeName) && e.href ? 0 : -1;
        }
      }
    },
    propFix: {
      "for": "htmlFor",
      "class": "className"
    }
  }), y.optSelected || (S.propHooks.selected = {
    get: function get(e) {
      var t = e.parentNode;
      return t && t.parentNode && t.parentNode.selectedIndex, null;
    },
    set: function set(e) {
      var t = e.parentNode;
      t && (t.selectedIndex, t.parentNode && t.parentNode.selectedIndex);
    }
  }), S.each(["tabIndex", "readOnly", "maxLength", "cellSpacing", "cellPadding", "rowSpan", "colSpan", "useMap", "frameBorder", "contentEditable"], function () {
    S.propFix[this.toLowerCase()] = this;
  }), S.fn.extend({
    addClass: function addClass(t) {
      var e,
          n,
          r,
          i,
          o,
          a,
          s,
          u = 0;
      if (m(t)) return this.each(function (e) {
        S(this).addClass(t.call(this, e, yt(this)));
      });
      if ((e = mt(t)).length) while (n = this[u++]) {
        if (i = yt(n), r = 1 === n.nodeType && " " + vt(i) + " ") {
          a = 0;

          while (o = e[a++]) {
            r.indexOf(" " + o + " ") < 0 && (r += o + " ");
          }

          i !== (s = vt(r)) && n.setAttribute("class", s);
        }
      }
      return this;
    },
    removeClass: function removeClass(t) {
      var e,
          n,
          r,
          i,
          o,
          a,
          s,
          u = 0;
      if (m(t)) return this.each(function (e) {
        S(this).removeClass(t.call(this, e, yt(this)));
      });
      if (!arguments.length) return this.attr("class", "");
      if ((e = mt(t)).length) while (n = this[u++]) {
        if (i = yt(n), r = 1 === n.nodeType && " " + vt(i) + " ") {
          a = 0;

          while (o = e[a++]) {
            while (-1 < r.indexOf(" " + o + " ")) {
              r = r.replace(" " + o + " ", " ");
            }
          }

          i !== (s = vt(r)) && n.setAttribute("class", s);
        }
      }
      return this;
    },
    toggleClass: function toggleClass(i, t) {
      var o = _typeof(i),
          a = "string" === o || Array.isArray(i);

      return "boolean" == typeof t && a ? t ? this.addClass(i) : this.removeClass(i) : m(i) ? this.each(function (e) {
        S(this).toggleClass(i.call(this, e, yt(this), t), t);
      }) : this.each(function () {
        var e, t, n, r;

        if (a) {
          t = 0, n = S(this), r = mt(i);

          while (e = r[t++]) {
            n.hasClass(e) ? n.removeClass(e) : n.addClass(e);
          }
        } else void 0 !== i && "boolean" !== o || ((e = yt(this)) && Y.set(this, "__className__", e), this.setAttribute && this.setAttribute("class", e || !1 === i ? "" : Y.get(this, "__className__") || ""));
      });
    },
    hasClass: function hasClass(e) {
      var t,
          n,
          r = 0;
      t = " " + e + " ";

      while (n = this[r++]) {
        if (1 === n.nodeType && -1 < (" " + vt(yt(n)) + " ").indexOf(t)) return !0;
      }

      return !1;
    }
  });
  var xt = /\r/g;
  S.fn.extend({
    val: function val(n) {
      var r,
          e,
          i,
          t = this[0];
      return arguments.length ? (i = m(n), this.each(function (e) {
        var t;
        1 === this.nodeType && (null == (t = i ? n.call(this, e, S(this).val()) : n) ? t = "" : "number" == typeof t ? t += "" : Array.isArray(t) && (t = S.map(t, function (e) {
          return null == e ? "" : e + "";
        })), (r = S.valHooks[this.type] || S.valHooks[this.nodeName.toLowerCase()]) && "set" in r && void 0 !== r.set(this, t, "value") || (this.value = t));
      })) : t ? (r = S.valHooks[t.type] || S.valHooks[t.nodeName.toLowerCase()]) && "get" in r && void 0 !== (e = r.get(t, "value")) ? e : "string" == typeof (e = t.value) ? e.replace(xt, "") : null == e ? "" : e : void 0;
    }
  }), S.extend({
    valHooks: {
      option: {
        get: function get(e) {
          var t = S.find.attr(e, "value");
          return null != t ? t : vt(S.text(e));
        }
      },
      select: {
        get: function get(e) {
          var t,
              n,
              r,
              i = e.options,
              o = e.selectedIndex,
              a = "select-one" === e.type,
              s = a ? null : [],
              u = a ? o + 1 : i.length;

          for (r = o < 0 ? u : a ? o : 0; r < u; r++) {
            if (((n = i[r]).selected || r === o) && !n.disabled && (!n.parentNode.disabled || !A(n.parentNode, "optgroup"))) {
              if (t = S(n).val(), a) return t;
              s.push(t);
            }
          }

          return s;
        },
        set: function set(e, t) {
          var n,
              r,
              i = e.options,
              o = S.makeArray(t),
              a = i.length;

          while (a--) {
            ((r = i[a]).selected = -1 < S.inArray(S.valHooks.option.get(r), o)) && (n = !0);
          }

          return n || (e.selectedIndex = -1), o;
        }
      }
    }
  }), S.each(["radio", "checkbox"], function () {
    S.valHooks[this] = {
      set: function set(e, t) {
        if (Array.isArray(t)) return e.checked = -1 < S.inArray(S(e).val(), t);
      }
    }, y.checkOn || (S.valHooks[this].get = function (e) {
      return null === e.getAttribute("value") ? "on" : e.value;
    });
  }), y.focusin = "onfocusin" in C;

  var bt = /^(?:focusinfocus|focusoutblur)$/,
      wt = function wt(e) {
    e.stopPropagation();
  };

  S.extend(S.event, {
    trigger: function trigger(e, t, n, r) {
      var i,
          o,
          a,
          s,
          u,
          l,
          c,
          f,
          p = [n || E],
          d = v.call(e, "type") ? e.type : e,
          h = v.call(e, "namespace") ? e.namespace.split(".") : [];

      if (o = f = a = n = n || E, 3 !== n.nodeType && 8 !== n.nodeType && !bt.test(d + S.event.triggered) && (-1 < d.indexOf(".") && (d = (h = d.split(".")).shift(), h.sort()), u = d.indexOf(":") < 0 && "on" + d, (e = e[S.expando] ? e : new S.Event(d, "object" == _typeof(e) && e)).isTrigger = r ? 2 : 3, e.namespace = h.join("."), e.rnamespace = e.namespace ? new RegExp("(^|\\.)" + h.join("\\.(?:.*\\.|)") + "(\\.|$)") : null, e.result = void 0, e.target || (e.target = n), t = null == t ? [e] : S.makeArray(t, [e]), c = S.event.special[d] || {}, r || !c.trigger || !1 !== c.trigger.apply(n, t))) {
        if (!r && !c.noBubble && !x(n)) {
          for (s = c.delegateType || d, bt.test(s + d) || (o = o.parentNode); o; o = o.parentNode) {
            p.push(o), a = o;
          }

          a === (n.ownerDocument || E) && p.push(a.defaultView || a.parentWindow || C);
        }

        i = 0;

        while ((o = p[i++]) && !e.isPropagationStopped()) {
          f = o, e.type = 1 < i ? s : c.bindType || d, (l = (Y.get(o, "events") || Object.create(null))[e.type] && Y.get(o, "handle")) && l.apply(o, t), (l = u && o[u]) && l.apply && V(o) && (e.result = l.apply(o, t), !1 === e.result && e.preventDefault());
        }

        return e.type = d, r || e.isDefaultPrevented() || c._default && !1 !== c._default.apply(p.pop(), t) || !V(n) || u && m(n[d]) && !x(n) && ((a = n[u]) && (n[u] = null), S.event.triggered = d, e.isPropagationStopped() && f.addEventListener(d, wt), n[d](), e.isPropagationStopped() && f.removeEventListener(d, wt), S.event.triggered = void 0, a && (n[u] = a)), e.result;
      }
    },
    simulate: function simulate(e, t, n) {
      var r = S.extend(new S.Event(), n, {
        type: e,
        isSimulated: !0
      });
      S.event.trigger(r, null, t);
    }
  }), S.fn.extend({
    trigger: function trigger(e, t) {
      return this.each(function () {
        S.event.trigger(e, t, this);
      });
    },
    triggerHandler: function triggerHandler(e, t) {
      var n = this[0];
      if (n) return S.event.trigger(e, t, n, !0);
    }
  }), y.focusin || S.each({
    focus: "focusin",
    blur: "focusout"
  }, function (n, r) {
    var i = function i(e) {
      S.event.simulate(r, e.target, S.event.fix(e));
    };

    S.event.special[r] = {
      setup: function setup() {
        var e = this.ownerDocument || this.document || this,
            t = Y.access(e, r);
        t || e.addEventListener(n, i, !0), Y.access(e, r, (t || 0) + 1);
      },
      teardown: function teardown() {
        var e = this.ownerDocument || this.document || this,
            t = Y.access(e, r) - 1;
        t ? Y.access(e, r, t) : (e.removeEventListener(n, i, !0), Y.remove(e, r));
      }
    };
  });
  var Tt = C.location,
      Ct = {
    guid: Date.now()
  },
      Et = /\?/;

  S.parseXML = function (e) {
    var t;
    if (!e || "string" != typeof e) return null;

    try {
      t = new C.DOMParser().parseFromString(e, "text/xml");
    } catch (e) {
      t = void 0;
    }

    return t && !t.getElementsByTagName("parsererror").length || S.error("Invalid XML: " + e), t;
  };

  var St = /\[\]$/,
      kt = /\r?\n/g,
      At = /^(?:submit|button|image|reset|file)$/i,
      Nt = /^(?:input|select|textarea|keygen)/i;

  function Dt(n, e, r, i) {
    var t;
    if (Array.isArray(e)) S.each(e, function (e, t) {
      r || St.test(n) ? i(n, t) : Dt(n + "[" + ("object" == _typeof(t) && null != t ? e : "") + "]", t, r, i);
    });else if (r || "object" !== w(e)) i(n, e);else for (t in e) {
      Dt(n + "[" + t + "]", e[t], r, i);
    }
  }

  S.param = function (e, t) {
    var n,
        r = [],
        i = function i(e, t) {
      var n = m(t) ? t() : t;
      r[r.length] = encodeURIComponent(e) + "=" + encodeURIComponent(null == n ? "" : n);
    };

    if (null == e) return "";
    if (Array.isArray(e) || e.jquery && !S.isPlainObject(e)) S.each(e, function () {
      i(this.name, this.value);
    });else for (n in e) {
      Dt(n, e[n], t, i);
    }
    return r.join("&");
  }, S.fn.extend({
    serialize: function serialize() {
      return S.param(this.serializeArray());
    },
    serializeArray: function serializeArray() {
      return this.map(function () {
        var e = S.prop(this, "elements");
        return e ? S.makeArray(e) : this;
      }).filter(function () {
        var e = this.type;
        return this.name && !S(this).is(":disabled") && Nt.test(this.nodeName) && !At.test(e) && (this.checked || !pe.test(e));
      }).map(function (e, t) {
        var n = S(this).val();
        return null == n ? null : Array.isArray(n) ? S.map(n, function (e) {
          return {
            name: t.name,
            value: e.replace(kt, "\r\n")
          };
        }) : {
          name: t.name,
          value: n.replace(kt, "\r\n")
        };
      }).get();
    }
  });
  var jt = /%20/g,
      qt = /#.*$/,
      Lt = /([?&])_=[^&]*/,
      Ht = /^(.*?):[ \t]*([^\r\n]*)$/gm,
      Ot = /^(?:GET|HEAD)$/,
      Pt = /^\/\//,
      Rt = {},
      Mt = {},
      It = "*/".concat("*"),
      Wt = E.createElement("a");

  function Ft(o) {
    return function (e, t) {
      "string" != typeof e && (t = e, e = "*");
      var n,
          r = 0,
          i = e.toLowerCase().match(P) || [];
      if (m(t)) while (n = i[r++]) {
        "+" === n[0] ? (n = n.slice(1) || "*", (o[n] = o[n] || []).unshift(t)) : (o[n] = o[n] || []).push(t);
      }
    };
  }

  function Bt(t, i, o, a) {
    var s = {},
        u = t === Mt;

    function l(e) {
      var r;
      return s[e] = !0, S.each(t[e] || [], function (e, t) {
        var n = t(i, o, a);
        return "string" != typeof n || u || s[n] ? u ? !(r = n) : void 0 : (i.dataTypes.unshift(n), l(n), !1);
      }), r;
    }

    return l(i.dataTypes[0]) || !s["*"] && l("*");
  }

  function $t(e, t) {
    var n,
        r,
        i = S.ajaxSettings.flatOptions || {};

    for (n in t) {
      void 0 !== t[n] && ((i[n] ? e : r || (r = {}))[n] = t[n]);
    }

    return r && S.extend(!0, e, r), e;
  }

  Wt.href = Tt.href, S.extend({
    active: 0,
    lastModified: {},
    etag: {},
    ajaxSettings: {
      url: Tt.href,
      type: "GET",
      isLocal: /^(?:about|app|app-storage|.+-extension|file|res|widget):$/.test(Tt.protocol),
      global: !0,
      processData: !0,
      async: !0,
      contentType: "application/x-www-form-urlencoded; charset=UTF-8",
      accepts: {
        "*": It,
        text: "text/plain",
        html: "text/html",
        xml: "application/xml, text/xml",
        json: "application/json, text/javascript"
      },
      contents: {
        xml: /\bxml\b/,
        html: /\bhtml/,
        json: /\bjson\b/
      },
      responseFields: {
        xml: "responseXML",
        text: "responseText",
        json: "responseJSON"
      },
      converters: {
        "* text": String,
        "text html": !0,
        "text json": JSON.parse,
        "text xml": S.parseXML
      },
      flatOptions: {
        url: !0,
        context: !0
      }
    },
    ajaxSetup: function ajaxSetup(e, t) {
      return t ? $t($t(e, S.ajaxSettings), t) : $t(S.ajaxSettings, e);
    },
    ajaxPrefilter: Ft(Rt),
    ajaxTransport: Ft(Mt),
    ajax: function ajax(e, t) {
      "object" == _typeof(e) && (t = e, e = void 0), t = t || {};
      var c,
          f,
          p,
          n,
          d,
          r,
          h,
          g,
          i,
          o,
          v = S.ajaxSetup({}, t),
          y = v.context || v,
          m = v.context && (y.nodeType || y.jquery) ? S(y) : S.event,
          x = S.Deferred(),
          b = S.Callbacks("once memory"),
          w = v.statusCode || {},
          a = {},
          s = {},
          u = "canceled",
          T = {
        readyState: 0,
        getResponseHeader: function getResponseHeader(e) {
          var t;

          if (h) {
            if (!n) {
              n = {};

              while (t = Ht.exec(p)) {
                n[t[1].toLowerCase() + " "] = (n[t[1].toLowerCase() + " "] || []).concat(t[2]);
              }
            }

            t = n[e.toLowerCase() + " "];
          }

          return null == t ? null : t.join(", ");
        },
        getAllResponseHeaders: function getAllResponseHeaders() {
          return h ? p : null;
        },
        setRequestHeader: function setRequestHeader(e, t) {
          return null == h && (e = s[e.toLowerCase()] = s[e.toLowerCase()] || e, a[e] = t), this;
        },
        overrideMimeType: function overrideMimeType(e) {
          return null == h && (v.mimeType = e), this;
        },
        statusCode: function statusCode(e) {
          var t;
          if (e) if (h) T.always(e[T.status]);else for (t in e) {
            w[t] = [w[t], e[t]];
          }
          return this;
        },
        abort: function abort(e) {
          var t = e || u;
          return c && c.abort(t), l(0, t), this;
        }
      };

      if (x.promise(T), v.url = ((e || v.url || Tt.href) + "").replace(Pt, Tt.protocol + "//"), v.type = t.method || t.type || v.method || v.type, v.dataTypes = (v.dataType || "*").toLowerCase().match(P) || [""], null == v.crossDomain) {
        r = E.createElement("a");

        try {
          r.href = v.url, r.href = r.href, v.crossDomain = Wt.protocol + "//" + Wt.host != r.protocol + "//" + r.host;
        } catch (e) {
          v.crossDomain = !0;
        }
      }

      if (v.data && v.processData && "string" != typeof v.data && (v.data = S.param(v.data, v.traditional)), Bt(Rt, v, t, T), h) return T;

      for (i in (g = S.event && v.global) && 0 == S.active++ && S.event.trigger("ajaxStart"), v.type = v.type.toUpperCase(), v.hasContent = !Ot.test(v.type), f = v.url.replace(qt, ""), v.hasContent ? v.data && v.processData && 0 === (v.contentType || "").indexOf("application/x-www-form-urlencoded") && (v.data = v.data.replace(jt, "+")) : (o = v.url.slice(f.length), v.data && (v.processData || "string" == typeof v.data) && (f += (Et.test(f) ? "&" : "?") + v.data, delete v.data), !1 === v.cache && (f = f.replace(Lt, "$1"), o = (Et.test(f) ? "&" : "?") + "_=" + Ct.guid++ + o), v.url = f + o), v.ifModified && (S.lastModified[f] && T.setRequestHeader("If-Modified-Since", S.lastModified[f]), S.etag[f] && T.setRequestHeader("If-None-Match", S.etag[f])), (v.data && v.hasContent && !1 !== v.contentType || t.contentType) && T.setRequestHeader("Content-Type", v.contentType), T.setRequestHeader("Accept", v.dataTypes[0] && v.accepts[v.dataTypes[0]] ? v.accepts[v.dataTypes[0]] + ("*" !== v.dataTypes[0] ? ", " + It + "; q=0.01" : "") : v.accepts["*"]), v.headers) {
        T.setRequestHeader(i, v.headers[i]);
      }

      if (v.beforeSend && (!1 === v.beforeSend.call(y, T, v) || h)) return T.abort();

      if (u = "abort", b.add(v.complete), T.done(v.success), T.fail(v.error), c = Bt(Mt, v, t, T)) {
        if (T.readyState = 1, g && m.trigger("ajaxSend", [T, v]), h) return T;
        v.async && 0 < v.timeout && (d = C.setTimeout(function () {
          T.abort("timeout");
        }, v.timeout));

        try {
          h = !1, c.send(a, l);
        } catch (e) {
          if (h) throw e;
          l(-1, e);
        }
      } else l(-1, "No Transport");

      function l(e, t, n, r) {
        var i,
            o,
            a,
            s,
            u,
            l = t;
        h || (h = !0, d && C.clearTimeout(d), c = void 0, p = r || "", T.readyState = 0 < e ? 4 : 0, i = 200 <= e && e < 300 || 304 === e, n && (s = function (e, t, n) {
          var r,
              i,
              o,
              a,
              s = e.contents,
              u = e.dataTypes;

          while ("*" === u[0]) {
            u.shift(), void 0 === r && (r = e.mimeType || t.getResponseHeader("Content-Type"));
          }

          if (r) for (i in s) {
            if (s[i] && s[i].test(r)) {
              u.unshift(i);
              break;
            }
          }
          if (u[0] in n) o = u[0];else {
            for (i in n) {
              if (!u[0] || e.converters[i + " " + u[0]]) {
                o = i;
                break;
              }

              a || (a = i);
            }

            o = o || a;
          }
          if (o) return o !== u[0] && u.unshift(o), n[o];
        }(v, T, n)), !i && -1 < S.inArray("script", v.dataTypes) && (v.converters["text script"] = function () {}), s = function (e, t, n, r) {
          var i,
              o,
              a,
              s,
              u,
              l = {},
              c = e.dataTypes.slice();
          if (c[1]) for (a in e.converters) {
            l[a.toLowerCase()] = e.converters[a];
          }
          o = c.shift();

          while (o) {
            if (e.responseFields[o] && (n[e.responseFields[o]] = t), !u && r && e.dataFilter && (t = e.dataFilter(t, e.dataType)), u = o, o = c.shift()) if ("*" === o) o = u;else if ("*" !== u && u !== o) {
              if (!(a = l[u + " " + o] || l["* " + o])) for (i in l) {
                if ((s = i.split(" "))[1] === o && (a = l[u + " " + s[0]] || l["* " + s[0]])) {
                  !0 === a ? a = l[i] : !0 !== l[i] && (o = s[0], c.unshift(s[1]));
                  break;
                }
              }
              if (!0 !== a) if (a && e["throws"]) t = a(t);else try {
                t = a(t);
              } catch (e) {
                return {
                  state: "parsererror",
                  error: a ? e : "No conversion from " + u + " to " + o
                };
              }
            }
          }

          return {
            state: "success",
            data: t
          };
        }(v, s, T, i), i ? (v.ifModified && ((u = T.getResponseHeader("Last-Modified")) && (S.lastModified[f] = u), (u = T.getResponseHeader("etag")) && (S.etag[f] = u)), 204 === e || "HEAD" === v.type ? l = "nocontent" : 304 === e ? l = "notmodified" : (l = s.state, o = s.data, i = !(a = s.error))) : (a = l, !e && l || (l = "error", e < 0 && (e = 0))), T.status = e, T.statusText = (t || l) + "", i ? x.resolveWith(y, [o, l, T]) : x.rejectWith(y, [T, l, a]), T.statusCode(w), w = void 0, g && m.trigger(i ? "ajaxSuccess" : "ajaxError", [T, v, i ? o : a]), b.fireWith(y, [T, l]), g && (m.trigger("ajaxComplete", [T, v]), --S.active || S.event.trigger("ajaxStop")));
      }

      return T;
    },
    getJSON: function getJSON(e, t, n) {
      return S.get(e, t, n, "json");
    },
    getScript: function getScript(e, t) {
      return S.get(e, void 0, t, "script");
    }
  }), S.each(["get", "post"], function (e, i) {
    S[i] = function (e, t, n, r) {
      return m(t) && (r = r || n, n = t, t = void 0), S.ajax(S.extend({
        url: e,
        type: i,
        dataType: r,
        data: t,
        success: n
      }, S.isPlainObject(e) && e));
    };
  }), S.ajaxPrefilter(function (e) {
    var t;

    for (t in e.headers) {
      "content-type" === t.toLowerCase() && (e.contentType = e.headers[t] || "");
    }
  }), S._evalUrl = function (e, t, n) {
    return S.ajax({
      url: e,
      type: "GET",
      dataType: "script",
      cache: !0,
      async: !1,
      global: !1,
      converters: {
        "text script": function textScript() {}
      },
      dataFilter: function dataFilter(e) {
        S.globalEval(e, t, n);
      }
    });
  }, S.fn.extend({
    wrapAll: function wrapAll(e) {
      var t;
      return this[0] && (m(e) && (e = e.call(this[0])), t = S(e, this[0].ownerDocument).eq(0).clone(!0), this[0].parentNode && t.insertBefore(this[0]), t.map(function () {
        var e = this;

        while (e.firstElementChild) {
          e = e.firstElementChild;
        }

        return e;
      }).append(this)), this;
    },
    wrapInner: function wrapInner(n) {
      return m(n) ? this.each(function (e) {
        S(this).wrapInner(n.call(this, e));
      }) : this.each(function () {
        var e = S(this),
            t = e.contents();
        t.length ? t.wrapAll(n) : e.append(n);
      });
    },
    wrap: function wrap(t) {
      var n = m(t);
      return this.each(function (e) {
        S(this).wrapAll(n ? t.call(this, e) : t);
      });
    },
    unwrap: function unwrap(e) {
      return this.parent(e).not("body").each(function () {
        S(this).replaceWith(this.childNodes);
      }), this;
    }
  }), S.expr.pseudos.hidden = function (e) {
    return !S.expr.pseudos.visible(e);
  }, S.expr.pseudos.visible = function (e) {
    return !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  }, S.ajaxSettings.xhr = function () {
    try {
      return new C.XMLHttpRequest();
    } catch (e) {}
  };
  var _t = {
    0: 200,
    1223: 204
  },
      zt = S.ajaxSettings.xhr();
  y.cors = !!zt && "withCredentials" in zt, y.ajax = zt = !!zt, S.ajaxTransport(function (i) {
    var _o, a;

    if (y.cors || zt && !i.crossDomain) return {
      send: function send(e, t) {
        var n,
            r = i.xhr();
        if (r.open(i.type, i.url, i.async, i.username, i.password), i.xhrFields) for (n in i.xhrFields) {
          r[n] = i.xhrFields[n];
        }

        for (n in i.mimeType && r.overrideMimeType && r.overrideMimeType(i.mimeType), i.crossDomain || e["X-Requested-With"] || (e["X-Requested-With"] = "XMLHttpRequest"), e) {
          r.setRequestHeader(n, e[n]);
        }

        _o = function o(e) {
          return function () {
            _o && (_o = a = r.onload = r.onerror = r.onabort = r.ontimeout = r.onreadystatechange = null, "abort" === e ? r.abort() : "error" === e ? "number" != typeof r.status ? t(0, "error") : t(r.status, r.statusText) : t(_t[r.status] || r.status, r.statusText, "text" !== (r.responseType || "text") || "string" != typeof r.responseText ? {
              binary: r.response
            } : {
              text: r.responseText
            }, r.getAllResponseHeaders()));
          };
        }, r.onload = _o(), a = r.onerror = r.ontimeout = _o("error"), void 0 !== r.onabort ? r.onabort = a : r.onreadystatechange = function () {
          4 === r.readyState && C.setTimeout(function () {
            _o && a();
          });
        }, _o = _o("abort");

        try {
          r.send(i.hasContent && i.data || null);
        } catch (e) {
          if (_o) throw e;
        }
      },
      abort: function abort() {
        _o && _o();
      }
    };
  }), S.ajaxPrefilter(function (e) {
    e.crossDomain && (e.contents.script = !1);
  }), S.ajaxSetup({
    accepts: {
      script: "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript"
    },
    contents: {
      script: /\b(?:java|ecma)script\b/
    },
    converters: {
      "text script": function textScript(e) {
        return S.globalEval(e), e;
      }
    }
  }), S.ajaxPrefilter("script", function (e) {
    void 0 === e.cache && (e.cache = !1), e.crossDomain && (e.type = "GET");
  }), S.ajaxTransport("script", function (n) {
    var r, _i;

    if (n.crossDomain || n.scriptAttrs) return {
      send: function send(e, t) {
        r = S("<script>").attr(n.scriptAttrs || {}).prop({
          charset: n.scriptCharset,
          src: n.url
        }).on("load error", _i = function i(e) {
          r.remove(), _i = null, e && t("error" === e.type ? 404 : 200, e.type);
        }), E.head.appendChild(r[0]);
      },
      abort: function abort() {
        _i && _i();
      }
    };
  });
  var Ut,
      Xt = [],
      Vt = /(=)\?(?=&|$)|\?\?/;
  S.ajaxSetup({
    jsonp: "callback",
    jsonpCallback: function jsonpCallback() {
      var e = Xt.pop() || S.expando + "_" + Ct.guid++;
      return this[e] = !0, e;
    }
  }), S.ajaxPrefilter("json jsonp", function (e, t, n) {
    var r,
        i,
        o,
        a = !1 !== e.jsonp && (Vt.test(e.url) ? "url" : "string" == typeof e.data && 0 === (e.contentType || "").indexOf("application/x-www-form-urlencoded") && Vt.test(e.data) && "data");
    if (a || "jsonp" === e.dataTypes[0]) return r = e.jsonpCallback = m(e.jsonpCallback) ? e.jsonpCallback() : e.jsonpCallback, a ? e[a] = e[a].replace(Vt, "$1" + r) : !1 !== e.jsonp && (e.url += (Et.test(e.url) ? "&" : "?") + e.jsonp + "=" + r), e.converters["script json"] = function () {
      return o || S.error(r + " was not called"), o[0];
    }, e.dataTypes[0] = "json", i = C[r], C[r] = function () {
      o = arguments;
    }, n.always(function () {
      void 0 === i ? S(C).removeProp(r) : C[r] = i, e[r] && (e.jsonpCallback = t.jsonpCallback, Xt.push(r)), o && m(i) && i(o[0]), o = i = void 0;
    }), "script";
  }), y.createHTMLDocument = ((Ut = E.implementation.createHTMLDocument("").body).innerHTML = "<form></form><form></form>", 2 === Ut.childNodes.length), S.parseHTML = function (e, t, n) {
    return "string" != typeof e ? [] : ("boolean" == typeof t && (n = t, t = !1), t || (y.createHTMLDocument ? ((r = (t = E.implementation.createHTMLDocument("")).createElement("base")).href = E.location.href, t.head.appendChild(r)) : t = E), o = !n && [], (i = N.exec(e)) ? [t.createElement(i[1])] : (i = xe([e], t, o), o && o.length && S(o).remove(), S.merge([], i.childNodes)));
    var r, i, o;
  }, S.fn.load = function (e, t, n) {
    var r,
        i,
        o,
        a = this,
        s = e.indexOf(" ");
    return -1 < s && (r = vt(e.slice(s)), e = e.slice(0, s)), m(t) ? (n = t, t = void 0) : t && "object" == _typeof(t) && (i = "POST"), 0 < a.length && S.ajax({
      url: e,
      type: i || "GET",
      dataType: "html",
      data: t
    }).done(function (e) {
      o = arguments, a.html(r ? S("<div>").append(S.parseHTML(e)).find(r) : e);
    }).always(n && function (e, t) {
      a.each(function () {
        n.apply(this, o || [e.responseText, t, e]);
      });
    }), this;
  }, S.expr.pseudos.animated = function (t) {
    return S.grep(S.timers, function (e) {
      return t === e.elem;
    }).length;
  }, S.offset = {
    setOffset: function setOffset(e, t, n) {
      var r,
          i,
          o,
          a,
          s,
          u,
          l = S.css(e, "position"),
          c = S(e),
          f = {};
      "static" === l && (e.style.position = "relative"), s = c.offset(), o = S.css(e, "top"), u = S.css(e, "left"), ("absolute" === l || "fixed" === l) && -1 < (o + u).indexOf("auto") ? (a = (r = c.position()).top, i = r.left) : (a = parseFloat(o) || 0, i = parseFloat(u) || 0), m(t) && (t = t.call(e, n, S.extend({}, s))), null != t.top && (f.top = t.top - s.top + a), null != t.left && (f.left = t.left - s.left + i), "using" in t ? t.using.call(e, f) : ("number" == typeof f.top && (f.top += "px"), "number" == typeof f.left && (f.left += "px"), c.css(f));
    }
  }, S.fn.extend({
    offset: function offset(t) {
      if (arguments.length) return void 0 === t ? this : this.each(function (e) {
        S.offset.setOffset(this, t, e);
      });
      var e,
          n,
          r = this[0];
      return r ? r.getClientRects().length ? (e = r.getBoundingClientRect(), n = r.ownerDocument.defaultView, {
        top: e.top + n.pageYOffset,
        left: e.left + n.pageXOffset
      }) : {
        top: 0,
        left: 0
      } : void 0;
    },
    position: function position() {
      if (this[0]) {
        var e,
            t,
            n,
            r = this[0],
            i = {
          top: 0,
          left: 0
        };
        if ("fixed" === S.css(r, "position")) t = r.getBoundingClientRect();else {
          t = this.offset(), n = r.ownerDocument, e = r.offsetParent || n.documentElement;

          while (e && (e === n.body || e === n.documentElement) && "static" === S.css(e, "position")) {
            e = e.parentNode;
          }

          e && e !== r && 1 === e.nodeType && ((i = S(e).offset()).top += S.css(e, "borderTopWidth", !0), i.left += S.css(e, "borderLeftWidth", !0));
        }
        return {
          top: t.top - i.top - S.css(r, "marginTop", !0),
          left: t.left - i.left - S.css(r, "marginLeft", !0)
        };
      }
    },
    offsetParent: function offsetParent() {
      return this.map(function () {
        var e = this.offsetParent;

        while (e && "static" === S.css(e, "position")) {
          e = e.offsetParent;
        }

        return e || re;
      });
    }
  }), S.each({
    scrollLeft: "pageXOffset",
    scrollTop: "pageYOffset"
  }, function (t, i) {
    var o = "pageYOffset" === i;

    S.fn[t] = function (e) {
      return $(this, function (e, t, n) {
        var r;
        if (x(e) ? r = e : 9 === e.nodeType && (r = e.defaultView), void 0 === n) return r ? r[i] : e[t];
        r ? r.scrollTo(o ? r.pageXOffset : n, o ? n : r.pageYOffset) : e[t] = n;
      }, t, e, arguments.length);
    };
  }), S.each(["top", "left"], function (e, n) {
    S.cssHooks[n] = $e(y.pixelPosition, function (e, t) {
      if (t) return t = Be(e, n), Me.test(t) ? S(e).position()[n] + "px" : t;
    });
  }), S.each({
    Height: "height",
    Width: "width"
  }, function (a, s) {
    S.each({
      padding: "inner" + a,
      content: s,
      "": "outer" + a
    }, function (r, o) {
      S.fn[o] = function (e, t) {
        var n = arguments.length && (r || "boolean" != typeof e),
            i = r || (!0 === e || !0 === t ? "margin" : "border");
        return $(this, function (e, t, n) {
          var r;
          return x(e) ? 0 === o.indexOf("outer") ? e["inner" + a] : e.document.documentElement["client" + a] : 9 === e.nodeType ? (r = e.documentElement, Math.max(e.body["scroll" + a], r["scroll" + a], e.body["offset" + a], r["offset" + a], r["client" + a])) : void 0 === n ? S.css(e, t, i) : S.style(e, t, n, i);
        }, s, n ? e : void 0, n);
      };
    });
  }), S.each(["ajaxStart", "ajaxStop", "ajaxComplete", "ajaxError", "ajaxSuccess", "ajaxSend"], function (e, t) {
    S.fn[t] = function (e) {
      return this.on(t, e);
    };
  }), S.fn.extend({
    bind: function bind(e, t, n) {
      return this.on(e, null, t, n);
    },
    unbind: function unbind(e, t) {
      return this.off(e, null, t);
    },
    delegate: function delegate(e, t, n, r) {
      return this.on(t, e, n, r);
    },
    undelegate: function undelegate(e, t, n) {
      return 1 === arguments.length ? this.off(e, "**") : this.off(t, e || "**", n);
    },
    hover: function hover(e, t) {
      return this.mouseenter(e).mouseleave(t || e);
    }
  }), S.each("blur focus focusin focusout resize scroll click dblclick mousedown mouseup mousemove mouseover mouseout mouseenter mouseleave change select submit keydown keypress keyup contextmenu".split(" "), function (e, n) {
    S.fn[n] = function (e, t) {
      return 0 < arguments.length ? this.on(n, null, e, t) : this.trigger(n);
    };
  });
  var Gt = /^[\s\uFEFF\xA0]+|[\s\uFEFF\xA0]+$/g;
  S.proxy = function (e, t) {
    var n, r, i;
    if ("string" == typeof t && (n = e[t], t = e, e = n), m(e)) return r = s.call(arguments, 2), (i = function i() {
      return e.apply(t || this, r.concat(s.call(arguments)));
    }).guid = e.guid = e.guid || S.guid++, i;
  }, S.holdReady = function (e) {
    e ? S.readyWait++ : S.ready(!0);
  }, S.isArray = Array.isArray, S.parseJSON = JSON.parse, S.nodeName = A, S.isFunction = m, S.isWindow = x, S.camelCase = X, S.type = w, S.now = Date.now, S.isNumeric = function (e) {
    var t = S.type(e);
    return ("number" === t || "string" === t) && !isNaN(e - parseFloat(e));
  }, S.trim = function (e) {
    return null == e ? "" : (e + "").replace(Gt, "");
  },  true && !(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = (function () {
    return S;
  }).apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__),
				__WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
  var Yt = C.jQuery,
      Qt = C.$;
  return S.noConflict = function (e) {
    return C.$ === S && (C.$ = Qt), e && C.jQuery === S && (C.jQuery = Yt), S;
  }, "undefined" == typeof e && (C.jQuery = C.$ = S), S;
});
/* WEBPACK VAR INJECTION */}.call(this, __webpack_require__(38)(module)))

/***/ }),

/***/ 37:
/***/ (function(module, exports, __webpack_require__) {

var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

//     Underscore.js 1.6.0
//     http://underscorejs.org
//     (c) 2009-2014 Jeremy Ashkenas, DocumentCloud and Investigative Reporters & Editors
//     Underscore may be freely distributed under the MIT license.
(function () {
  // Baseline setup
  // --------------
  // Establish the root object, `window` in the browser, or `exports` on the server.
  var root = this; // Save the previous value of the `_` variable.

  var previousUnderscore = root._; // Establish the object that gets returned to break out of a loop iteration.

  var breaker = {}; // Save bytes in the minified (but not gzipped) version:

  var ArrayProto = Array.prototype,
      ObjProto = Object.prototype,
      FuncProto = Function.prototype; // Create quick reference variables for speed access to core prototypes.

  var push = ArrayProto.push,
      slice = ArrayProto.slice,
      concat = ArrayProto.concat,
      toString = ObjProto.toString,
      hasOwnProperty = ObjProto.hasOwnProperty; // All **ECMAScript 5** native function implementations that we hope to use
  // are declared here.

  var nativeForEach = ArrayProto.forEach,
      nativeMap = ArrayProto.map,
      nativeReduce = ArrayProto.reduce,
      nativeReduceRight = ArrayProto.reduceRight,
      nativeFilter = ArrayProto.filter,
      nativeEvery = ArrayProto.every,
      nativeSome = ArrayProto.some,
      nativeIndexOf = ArrayProto.indexOf,
      nativeLastIndexOf = ArrayProto.lastIndexOf,
      nativeIsArray = Array.isArray,
      nativeKeys = Object.keys,
      nativeBind = FuncProto.bind; // Create a safe reference to the Underscore object for use below.

  var _ = function _(obj) {
    if (obj instanceof _) return obj;
    if (!(this instanceof _)) return new _(obj);
    this._wrapped = obj;
  }; // Export the Underscore object for **Node.js**, with
  // backwards-compatibility for the old `require()` API. If we're in
  // the browser, add `_` as a global object via a string identifier,
  // for Closure Compiler "advanced" mode.


  if (true) {
    if ( true && module.exports) {
      exports = module.exports = _;
    }

    exports._ = _;
  } else {} // Current version.


  _.VERSION = '1.6.0'; // Collection Functions
  // --------------------
  // The cornerstone, an `each` implementation, aka `forEach`.
  // Handles objects with the built-in `forEach`, arrays, and raw objects.
  // Delegates to **ECMAScript 5**'s native `forEach` if available.

  var each = _.each = _.forEach = function (obj, iterator, context) {
    if (obj == null) return obj;

    if (nativeForEach && obj.forEach === nativeForEach) {
      obj.forEach(iterator, context);
    } else if (obj.length === +obj.length) {
      for (var i = 0, length = obj.length; i < length; i++) {
        if (iterator.call(context, obj[i], i, obj) === breaker) return;
      }
    } else {
      var keys = _.keys(obj);

      for (var i = 0, length = keys.length; i < length; i++) {
        if (iterator.call(context, obj[keys[i]], keys[i], obj) === breaker) return;
      }
    }

    return obj;
  }; // Return the results of applying the iterator to each element.
  // Delegates to **ECMAScript 5**'s native `map` if available.


  _.map = _.collect = function (obj, iterator, context) {
    var results = [];
    if (obj == null) return results;
    if (nativeMap && obj.map === nativeMap) return obj.map(iterator, context);
    each(obj, function (value, index, list) {
      results.push(iterator.call(context, value, index, list));
    });
    return results;
  };

  var reduceError = 'Reduce of empty array with no initial value'; // **Reduce** builds up a single result from a list of values, aka `inject`,
  // or `foldl`. Delegates to **ECMAScript 5**'s native `reduce` if available.

  _.reduce = _.foldl = _.inject = function (obj, iterator, memo, context) {
    var initial = arguments.length > 2;
    if (obj == null) obj = [];

    if (nativeReduce && obj.reduce === nativeReduce) {
      if (context) iterator = _.bind(iterator, context);
      return initial ? obj.reduce(iterator, memo) : obj.reduce(iterator);
    }

    each(obj, function (value, index, list) {
      if (!initial) {
        memo = value;
        initial = true;
      } else {
        memo = iterator.call(context, memo, value, index, list);
      }
    });
    if (!initial) throw new TypeError(reduceError);
    return memo;
  }; // The right-associative version of reduce, also known as `foldr`.
  // Delegates to **ECMAScript 5**'s native `reduceRight` if available.


  _.reduceRight = _.foldr = function (obj, iterator, memo, context) {
    var initial = arguments.length > 2;
    if (obj == null) obj = [];

    if (nativeReduceRight && obj.reduceRight === nativeReduceRight) {
      if (context) iterator = _.bind(iterator, context);
      return initial ? obj.reduceRight(iterator, memo) : obj.reduceRight(iterator);
    }

    var length = obj.length;

    if (length !== +length) {
      var keys = _.keys(obj);

      length = keys.length;
    }

    each(obj, function (value, index, list) {
      index = keys ? keys[--length] : --length;

      if (!initial) {
        memo = obj[index];
        initial = true;
      } else {
        memo = iterator.call(context, memo, obj[index], index, list);
      }
    });
    if (!initial) throw new TypeError(reduceError);
    return memo;
  }; // Return the first value which passes a truth test. Aliased as `detect`.


  _.find = _.detect = function (obj, predicate, context) {
    var result;
    any(obj, function (value, index, list) {
      if (predicate.call(context, value, index, list)) {
        result = value;
        return true;
      }
    });
    return result;
  }; // Return all the elements that pass a truth test.
  // Delegates to **ECMAScript 5**'s native `filter` if available.
  // Aliased as `select`.


  _.filter = _.select = function (obj, predicate, context) {
    var results = [];
    if (obj == null) return results;
    if (nativeFilter && obj.filter === nativeFilter) return obj.filter(predicate, context);
    each(obj, function (value, index, list) {
      if (predicate.call(context, value, index, list)) results.push(value);
    });
    return results;
  }; // Return all the elements for which a truth test fails.


  _.reject = function (obj, predicate, context) {
    return _.filter(obj, function (value, index, list) {
      return !predicate.call(context, value, index, list);
    }, context);
  }; // Determine whether all of the elements match a truth test.
  // Delegates to **ECMAScript 5**'s native `every` if available.
  // Aliased as `all`.


  _.every = _.all = function (obj, predicate, context) {
    predicate || (predicate = _.identity);
    var result = true;
    if (obj == null) return result;
    if (nativeEvery && obj.every === nativeEvery) return obj.every(predicate, context);
    each(obj, function (value, index, list) {
      if (!(result = result && predicate.call(context, value, index, list))) return breaker;
    });
    return !!result;
  }; // Determine if at least one element in the object matches a truth test.
  // Delegates to **ECMAScript 5**'s native `some` if available.
  // Aliased as `any`.


  var any = _.some = _.any = function (obj, predicate, context) {
    predicate || (predicate = _.identity);
    var result = false;
    if (obj == null) return result;
    if (nativeSome && obj.some === nativeSome) return obj.some(predicate, context);
    each(obj, function (value, index, list) {
      if (result || (result = predicate.call(context, value, index, list))) return breaker;
    });
    return !!result;
  }; // Determine if the array or object contains a given value (using `===`).
  // Aliased as `include`.


  _.contains = _.include = function (obj, target) {
    if (obj == null) return false;
    if (nativeIndexOf && obj.indexOf === nativeIndexOf) return obj.indexOf(target) != -1;
    return any(obj, function (value) {
      return value === target;
    });
  }; // Invoke a method (with arguments) on every item in a collection.


  _.invoke = function (obj, method) {
    var args = slice.call(arguments, 2);

    var isFunc = _.isFunction(method);

    return _.map(obj, function (value) {
      return (isFunc ? method : value[method]).apply(value, args);
    });
  }; // Convenience version of a common use case of `map`: fetching a property.


  _.pluck = function (obj, key) {
    return _.map(obj, _.property(key));
  }; // Convenience version of a common use case of `filter`: selecting only objects
  // containing specific `key:value` pairs.


  _.where = function (obj, attrs) {
    return _.filter(obj, _.matches(attrs));
  }; // Convenience version of a common use case of `find`: getting the first object
  // containing specific `key:value` pairs.


  _.findWhere = function (obj, attrs) {
    return _.find(obj, _.matches(attrs));
  }; // Return the maximum element or (element-based computation).
  // Can't optimize arrays of integers longer than 65,535 elements.
  // See [WebKit Bug 80797](https://bugs.webkit.org/show_bug.cgi?id=80797)


  _.max = function (obj, iterator, context) {
    if (!iterator && _.isArray(obj) && obj[0] === +obj[0] && obj.length < 65535) {
      return Math.max.apply(Math, obj);
    }

    var result = -Infinity,
        lastComputed = -Infinity;
    each(obj, function (value, index, list) {
      var computed = iterator ? iterator.call(context, value, index, list) : value;

      if (computed > lastComputed) {
        result = value;
        lastComputed = computed;
      }
    });
    return result;
  }; // Return the minimum element (or element-based computation).


  _.min = function (obj, iterator, context) {
    if (!iterator && _.isArray(obj) && obj[0] === +obj[0] && obj.length < 65535) {
      return Math.min.apply(Math, obj);
    }

    var result = Infinity,
        lastComputed = Infinity;
    each(obj, function (value, index, list) {
      var computed = iterator ? iterator.call(context, value, index, list) : value;

      if (computed < lastComputed) {
        result = value;
        lastComputed = computed;
      }
    });
    return result;
  }; // Shuffle an array, using the modern version of the
  // [Fisher-Yates shuffle](http://en.wikipedia.org/wiki/Fisher–Yates_shuffle).


  _.shuffle = function (obj) {
    var rand;
    var index = 0;
    var shuffled = [];
    each(obj, function (value) {
      rand = _.random(index++);
      shuffled[index - 1] = shuffled[rand];
      shuffled[rand] = value;
    });
    return shuffled;
  }; // Sample **n** random values from a collection.
  // If **n** is not specified, returns a single random element.
  // The internal `guard` argument allows it to work with `map`.


  _.sample = function (obj, n, guard) {
    if (n == null || guard) {
      if (obj.length !== +obj.length) obj = _.values(obj);
      return obj[_.random(obj.length - 1)];
    }

    return _.shuffle(obj).slice(0, Math.max(0, n));
  }; // An internal function to generate lookup iterators.


  var lookupIterator = function lookupIterator(value) {
    if (value == null) return _.identity;
    if (_.isFunction(value)) return value;
    return _.property(value);
  }; // Sort the object's values by a criterion produced by an iterator.


  _.sortBy = function (obj, iterator, context) {
    iterator = lookupIterator(iterator);
    return _.pluck(_.map(obj, function (value, index, list) {
      return {
        value: value,
        index: index,
        criteria: iterator.call(context, value, index, list)
      };
    }).sort(function (left, right) {
      var a = left.criteria;
      var b = right.criteria;

      if (a !== b) {
        if (a > b || a === void 0) return 1;
        if (a < b || b === void 0) return -1;
      }

      return left.index - right.index;
    }), 'value');
  }; // An internal function used for aggregate "group by" operations.


  var group = function group(behavior) {
    return function (obj, iterator, context) {
      var result = {};
      iterator = lookupIterator(iterator);
      each(obj, function (value, index) {
        var key = iterator.call(context, value, index, obj);
        behavior(result, key, value);
      });
      return result;
    };
  }; // Groups the object's values by a criterion. Pass either a string attribute
  // to group by, or a function that returns the criterion.


  _.groupBy = group(function (result, key, value) {
    _.has(result, key) ? result[key].push(value) : result[key] = [value];
  }); // Indexes the object's values by a criterion, similar to `groupBy`, but for
  // when you know that your index values will be unique.

  _.indexBy = group(function (result, key, value) {
    result[key] = value;
  }); // Counts instances of an object that group by a certain criterion. Pass
  // either a string attribute to count by, or a function that returns the
  // criterion.

  _.countBy = group(function (result, key) {
    _.has(result, key) ? result[key]++ : result[key] = 1;
  }); // Use a comparator function to figure out the smallest index at which
  // an object should be inserted so as to maintain order. Uses binary search.

  _.sortedIndex = function (array, obj, iterator, context) {
    iterator = lookupIterator(iterator);
    var value = iterator.call(context, obj);
    var low = 0,
        high = array.length;

    while (low < high) {
      var mid = low + high >>> 1;
      iterator.call(context, array[mid]) < value ? low = mid + 1 : high = mid;
    }

    return low;
  }; // Safely create a real, live array from anything iterable.


  _.toArray = function (obj) {
    if (!obj) return [];
    if (_.isArray(obj)) return slice.call(obj);
    if (obj.length === +obj.length) return _.map(obj, _.identity);
    return _.values(obj);
  }; // Return the number of elements in an object.


  _.size = function (obj) {
    if (obj == null) return 0;
    return obj.length === +obj.length ? obj.length : _.keys(obj).length;
  }; // Array Functions
  // ---------------
  // Get the first element of an array. Passing **n** will return the first N
  // values in the array. Aliased as `head` and `take`. The **guard** check
  // allows it to work with `_.map`.


  _.first = _.head = _.take = function (array, n, guard) {
    if (array == null) return void 0;
    if (n == null || guard) return array[0];
    if (n < 0) return [];
    return slice.call(array, 0, n);
  }; // Returns everything but the last entry of the array. Especially useful on
  // the arguments object. Passing **n** will return all the values in
  // the array, excluding the last N. The **guard** check allows it to work with
  // `_.map`.


  _.initial = function (array, n, guard) {
    return slice.call(array, 0, array.length - (n == null || guard ? 1 : n));
  }; // Get the last element of an array. Passing **n** will return the last N
  // values in the array. The **guard** check allows it to work with `_.map`.


  _.last = function (array, n, guard) {
    if (array == null) return void 0;
    if (n == null || guard) return array[array.length - 1];
    return slice.call(array, Math.max(array.length - n, 0));
  }; // Returns everything but the first entry of the array. Aliased as `tail` and `drop`.
  // Especially useful on the arguments object. Passing an **n** will return
  // the rest N values in the array. The **guard**
  // check allows it to work with `_.map`.


  _.rest = _.tail = _.drop = function (array, n, guard) {
    return slice.call(array, n == null || guard ? 1 : n);
  }; // Trim out all falsy values from an array.


  _.compact = function (array) {
    return _.filter(array, _.identity);
  }; // Internal implementation of a recursive `flatten` function.


  var flatten = function flatten(input, shallow, output) {
    if (shallow && _.every(input, _.isArray)) {
      return concat.apply(output, input);
    }

    each(input, function (value) {
      if (_.isArray(value) || _.isArguments(value)) {
        shallow ? push.apply(output, value) : flatten(value, shallow, output);
      } else {
        output.push(value);
      }
    });
    return output;
  }; // Flatten out an array, either recursively (by default), or just one level.


  _.flatten = function (array, shallow) {
    return flatten(array, shallow, []);
  }; // Return a version of the array that does not contain the specified value(s).


  _.without = function (array) {
    return _.difference(array, slice.call(arguments, 1));
  }; // Split an array into two arrays: one whose elements all satisfy the given
  // predicate, and one whose elements all do not satisfy the predicate.


  _.partition = function (array, predicate, context) {
    predicate = lookupIterator(predicate);
    var pass = [],
        fail = [];
    each(array, function (elem) {
      (predicate.call(context, elem) ? pass : fail).push(elem);
    });
    return [pass, fail];
  }; // Produce a duplicate-free version of the array. If the array has already
  // been sorted, you have the option of using a faster algorithm.
  // Aliased as `unique`.


  _.uniq = _.unique = function (array, isSorted, iterator, context) {
    if (_.isFunction(isSorted)) {
      context = iterator;
      iterator = isSorted;
      isSorted = false;
    }

    var initial = iterator ? _.map(array, iterator, context) : array;
    var results = [];
    var seen = [];
    each(initial, function (value, index) {
      if (isSorted ? !index || seen[seen.length - 1] !== value : !_.contains(seen, value)) {
        seen.push(value);
        results.push(array[index]);
      }
    });
    return results;
  }; // Produce an array that contains the union: each distinct element from all of
  // the passed-in arrays.


  _.union = function () {
    return _.uniq(_.flatten(arguments, true));
  }; // Produce an array that contains every item shared between all the
  // passed-in arrays.


  _.intersection = function (array) {
    var rest = slice.call(arguments, 1);
    return _.filter(_.uniq(array), function (item) {
      return _.every(rest, function (other) {
        return _.contains(other, item);
      });
    });
  }; // Take the difference between one array and a number of other arrays.
  // Only the elements present in just the first array will remain.


  _.difference = function (array) {
    var rest = concat.apply(ArrayProto, slice.call(arguments, 1));
    return _.filter(array, function (value) {
      return !_.contains(rest, value);
    });
  }; // Zip together multiple lists into a single array -- elements that share
  // an index go together.


  _.zip = function () {
    var length = _.max(_.pluck(arguments, 'length').concat(0));

    var results = new Array(length);

    for (var i = 0; i < length; i++) {
      results[i] = _.pluck(arguments, '' + i);
    }

    return results;
  }; // Converts lists into objects. Pass either a single array of `[key, value]`
  // pairs, or two parallel arrays of the same length -- one of keys, and one of
  // the corresponding values.


  _.object = function (list, values) {
    if (list == null) return {};
    var result = {};

    for (var i = 0, length = list.length; i < length; i++) {
      if (values) {
        result[list[i]] = values[i];
      } else {
        result[list[i][0]] = list[i][1];
      }
    }

    return result;
  }; // If the browser doesn't supply us with indexOf (I'm looking at you, **MSIE**),
  // we need this function. Return the position of the first occurrence of an
  // item in an array, or -1 if the item is not included in the array.
  // Delegates to **ECMAScript 5**'s native `indexOf` if available.
  // If the array is large and already in sort order, pass `true`
  // for **isSorted** to use binary search.


  _.indexOf = function (array, item, isSorted) {
    if (array == null) return -1;
    var i = 0,
        length = array.length;

    if (isSorted) {
      if (typeof isSorted == 'number') {
        i = isSorted < 0 ? Math.max(0, length + isSorted) : isSorted;
      } else {
        i = _.sortedIndex(array, item);
        return array[i] === item ? i : -1;
      }
    }

    if (nativeIndexOf && array.indexOf === nativeIndexOf) return array.indexOf(item, isSorted);

    for (; i < length; i++) {
      if (array[i] === item) return i;
    }

    return -1;
  }; // Delegates to **ECMAScript 5**'s native `lastIndexOf` if available.


  _.lastIndexOf = function (array, item, from) {
    if (array == null) return -1;
    var hasIndex = from != null;

    if (nativeLastIndexOf && array.lastIndexOf === nativeLastIndexOf) {
      return hasIndex ? array.lastIndexOf(item, from) : array.lastIndexOf(item);
    }

    var i = hasIndex ? from : array.length;

    while (i--) {
      if (array[i] === item) return i;
    }

    return -1;
  }; // Generate an integer Array containing an arithmetic progression. A port of
  // the native Python `range()` function. See
  // [the Python documentation](http://docs.python.org/library/functions.html#range).


  _.range = function (start, stop, step) {
    if (arguments.length <= 1) {
      stop = start || 0;
      start = 0;
    }

    step = arguments[2] || 1;
    var length = Math.max(Math.ceil((stop - start) / step), 0);
    var idx = 0;
    var range = new Array(length);

    while (idx < length) {
      range[idx++] = start;
      start += step;
    }

    return range;
  }; // Function (ahem) Functions
  // ------------------
  // Reusable constructor function for prototype setting.


  var ctor = function ctor() {}; // Create a function bound to a given object (assigning `this`, and arguments,
  // optionally). Delegates to **ECMAScript 5**'s native `Function.bind` if
  // available.


  _.bind = function (func, context) {
    var args, _bound;

    if (nativeBind && func.bind === nativeBind) return nativeBind.apply(func, slice.call(arguments, 1));
    if (!_.isFunction(func)) throw new TypeError();
    args = slice.call(arguments, 2);
    return _bound = function bound() {
      if (!(this instanceof _bound)) return func.apply(context, args.concat(slice.call(arguments)));
      ctor.prototype = func.prototype;
      var self = new ctor();
      ctor.prototype = null;
      var result = func.apply(self, args.concat(slice.call(arguments)));
      if (Object(result) === result) return result;
      return self;
    };
  }; // Partially apply a function by creating a version that has had some of its
  // arguments pre-filled, without changing its dynamic `this` context. _ acts
  // as a placeholder, allowing any combination of arguments to be pre-filled.


  _.partial = function (func) {
    var boundArgs = slice.call(arguments, 1);
    return function () {
      var position = 0;
      var args = boundArgs.slice();

      for (var i = 0, length = args.length; i < length; i++) {
        if (args[i] === _) args[i] = arguments[position++];
      }

      while (position < arguments.length) {
        args.push(arguments[position++]);
      }

      return func.apply(this, args);
    };
  }; // Bind a number of an object's methods to that object. Remaining arguments
  // are the method names to be bound. Useful for ensuring that all callbacks
  // defined on an object belong to it.


  _.bindAll = function (obj) {
    var funcs = slice.call(arguments, 1);
    if (funcs.length === 0) throw new Error('bindAll must be passed function names');
    each(funcs, function (f) {
      obj[f] = _.bind(obj[f], obj);
    });
    return obj;
  }; // Memoize an expensive function by storing its results.


  _.memoize = function (func, hasher) {
    var memo = {};
    hasher || (hasher = _.identity);
    return function () {
      var key = hasher.apply(this, arguments);
      return _.has(memo, key) ? memo[key] : memo[key] = func.apply(this, arguments);
    };
  }; // Delays a function for the given number of milliseconds, and then calls
  // it with the arguments supplied.


  _.delay = function (func, wait) {
    var args = slice.call(arguments, 2);
    return setTimeout(function () {
      return func.apply(null, args);
    }, wait);
  }; // Defers a function, scheduling it to run after the current call stack has
  // cleared.


  _.defer = function (func) {
    return _.delay.apply(_, [func, 1].concat(slice.call(arguments, 1)));
  }; // Returns a function, that, when invoked, will only be triggered at most once
  // during a given window of time. Normally, the throttled function will run
  // as much as it can, without ever going more than once per `wait` duration;
  // but if you'd like to disable the execution on the leading edge, pass
  // `{leading: false}`. To disable execution on the trailing edge, ditto.


  _.throttle = function (func, wait, options) {
    var context, args, result;
    var timeout = null;
    var previous = 0;
    options || (options = {});

    var later = function later() {
      previous = options.leading === false ? 0 : _.now();
      timeout = null;
      result = func.apply(context, args);
      context = args = null;
    };

    return function () {
      var now = _.now();

      if (!previous && options.leading === false) previous = now;
      var remaining = wait - (now - previous);
      context = this;
      args = arguments;

      if (remaining <= 0) {
        clearTimeout(timeout);
        timeout = null;
        previous = now;
        result = func.apply(context, args);
        context = args = null;
      } else if (!timeout && options.trailing !== false) {
        timeout = setTimeout(later, remaining);
      }

      return result;
    };
  }; // Returns a function, that, as long as it continues to be invoked, will not
  // be triggered. The function will be called after it stops being called for
  // N milliseconds. If `immediate` is passed, trigger the function on the
  // leading edge, instead of the trailing.


  _.debounce = function (func, wait, immediate) {
    var timeout, args, context, timestamp, result;

    var later = function later() {
      var last = _.now() - timestamp;

      if (last < wait) {
        timeout = setTimeout(later, wait - last);
      } else {
        timeout = null;

        if (!immediate) {
          result = func.apply(context, args);
          context = args = null;
        }
      }
    };

    return function () {
      context = this;
      args = arguments;
      timestamp = _.now();
      var callNow = immediate && !timeout;

      if (!timeout) {
        timeout = setTimeout(later, wait);
      }

      if (callNow) {
        result = func.apply(context, args);
        context = args = null;
      }

      return result;
    };
  }; // Returns a function that will be executed at most one time, no matter how
  // often you call it. Useful for lazy initialization.


  _.once = function (func) {
    var ran = false,
        memo;
    return function () {
      if (ran) return memo;
      ran = true;
      memo = func.apply(this, arguments);
      func = null;
      return memo;
    };
  }; // Returns the first function passed as an argument to the second,
  // allowing you to adjust arguments, run code before and after, and
  // conditionally execute the original function.


  _.wrap = function (func, wrapper) {
    return _.partial(wrapper, func);
  }; // Returns a function that is the composition of a list of functions, each
  // consuming the return value of the function that follows.


  _.compose = function () {
    var funcs = arguments;
    return function () {
      var args = arguments;

      for (var i = funcs.length - 1; i >= 0; i--) {
        args = [funcs[i].apply(this, args)];
      }

      return args[0];
    };
  }; // Returns a function that will only be executed after being called N times.


  _.after = function (times, func) {
    return function () {
      if (--times < 1) {
        return func.apply(this, arguments);
      }
    };
  }; // Object Functions
  // ----------------
  // Retrieve the names of an object's properties.
  // Delegates to **ECMAScript 5**'s native `Object.keys`


  _.keys = function (obj) {
    if (!_.isObject(obj)) return [];
    if (nativeKeys) return nativeKeys(obj);
    var keys = [];

    for (var key in obj) {
      if (_.has(obj, key)) keys.push(key);
    }

    return keys;
  }; // Retrieve the values of an object's properties.


  _.values = function (obj) {
    var keys = _.keys(obj);

    var length = keys.length;
    var values = new Array(length);

    for (var i = 0; i < length; i++) {
      values[i] = obj[keys[i]];
    }

    return values;
  }; // Convert an object into a list of `[key, value]` pairs.


  _.pairs = function (obj) {
    var keys = _.keys(obj);

    var length = keys.length;
    var pairs = new Array(length);

    for (var i = 0; i < length; i++) {
      pairs[i] = [keys[i], obj[keys[i]]];
    }

    return pairs;
  }; // Invert the keys and values of an object. The values must be serializable.


  _.invert = function (obj) {
    var result = {};

    var keys = _.keys(obj);

    for (var i = 0, length = keys.length; i < length; i++) {
      result[obj[keys[i]]] = keys[i];
    }

    return result;
  }; // Return a sorted list of the function names available on the object.
  // Aliased as `methods`


  _.functions = _.methods = function (obj) {
    var names = [];

    for (var key in obj) {
      if (_.isFunction(obj[key])) names.push(key);
    }

    return names.sort();
  }; // Extend a given object with all the properties in passed-in object(s).


  _.extend = function (obj) {
    each(slice.call(arguments, 1), function (source) {
      if (source) {
        for (var prop in source) {
          obj[prop] = source[prop];
        }
      }
    });
    return obj;
  }; // Return a copy of the object only containing the whitelisted properties.


  _.pick = function (obj) {
    var copy = {};
    var keys = concat.apply(ArrayProto, slice.call(arguments, 1));
    each(keys, function (key) {
      if (key in obj) copy[key] = obj[key];
    });
    return copy;
  }; // Return a copy of the object without the blacklisted properties.


  _.omit = function (obj) {
    var copy = {};
    var keys = concat.apply(ArrayProto, slice.call(arguments, 1));

    for (var key in obj) {
      if (!_.contains(keys, key)) copy[key] = obj[key];
    }

    return copy;
  }; // Fill in a given object with default properties.


  _.defaults = function (obj) {
    each(slice.call(arguments, 1), function (source) {
      if (source) {
        for (var prop in source) {
          if (obj[prop] === void 0) obj[prop] = source[prop];
        }
      }
    });
    return obj;
  }; // Create a (shallow-cloned) duplicate of an object.


  _.clone = function (obj) {
    if (!_.isObject(obj)) return obj;
    return _.isArray(obj) ? obj.slice() : _.extend({}, obj);
  }; // Invokes interceptor with the obj, and then returns obj.
  // The primary purpose of this method is to "tap into" a method chain, in
  // order to perform operations on intermediate results within the chain.


  _.tap = function (obj, interceptor) {
    interceptor(obj);
    return obj;
  }; // Internal recursive comparison function for `isEqual`.


  var eq = function eq(a, b, aStack, bStack) {
    // Identical objects are equal. `0 === -0`, but they aren't identical.
    // See the [Harmony `egal` proposal](http://wiki.ecmascript.org/doku.php?id=harmony:egal).
    if (a === b) return a !== 0 || 1 / a == 1 / b; // A strict comparison is necessary because `null == undefined`.

    if (a == null || b == null) return a === b; // Unwrap any wrapped objects.

    if (a instanceof _) a = a._wrapped;
    if (b instanceof _) b = b._wrapped; // Compare `[[Class]]` names.

    var className = toString.call(a);
    if (className != toString.call(b)) return false;

    switch (className) {
      // Strings, numbers, dates, and booleans are compared by value.
      case '[object String]':
        // Primitives and their corresponding object wrappers are equivalent; thus, `"5"` is
        // equivalent to `new String("5")`.
        return a == String(b);

      case '[object Number]':
        // `NaN`s are equivalent, but non-reflexive. An `egal` comparison is performed for
        // other numeric values.
        return a != +a ? b != +b : a == 0 ? 1 / a == 1 / b : a == +b;

      case '[object Date]':
      case '[object Boolean]':
        // Coerce dates and booleans to numeric primitive values. Dates are compared by their
        // millisecond representations. Note that invalid dates with millisecond representations
        // of `NaN` are not equivalent.
        return +a == +b;
      // RegExps are compared by their source patterns and flags.

      case '[object RegExp]':
        return a.source == b.source && a.global == b.global && a.multiline == b.multiline && a.ignoreCase == b.ignoreCase;
    }

    if (_typeof(a) != 'object' || _typeof(b) != 'object') return false; // Assume equality for cyclic structures. The algorithm for detecting cyclic
    // structures is adapted from ES 5.1 section 15.12.3, abstract operation `JO`.

    var length = aStack.length;

    while (length--) {
      // Linear search. Performance is inversely proportional to the number of
      // unique nested structures.
      if (aStack[length] == a) return bStack[length] == b;
    } // Objects with different constructors are not equivalent, but `Object`s
    // from different frames are.


    var aCtor = a.constructor,
        bCtor = b.constructor;

    if (aCtor !== bCtor && !(_.isFunction(aCtor) && aCtor instanceof aCtor && _.isFunction(bCtor) && bCtor instanceof bCtor) && 'constructor' in a && 'constructor' in b) {
      return false;
    } // Add the first object to the stack of traversed objects.


    aStack.push(a);
    bStack.push(b);
    var size = 0,
        result = true; // Recursively compare objects and arrays.

    if (className == '[object Array]') {
      // Compare array lengths to determine if a deep comparison is necessary.
      size = a.length;
      result = size == b.length;

      if (result) {
        // Deep compare the contents, ignoring non-numeric properties.
        while (size--) {
          if (!(result = eq(a[size], b[size], aStack, bStack))) break;
        }
      }
    } else {
      // Deep compare objects.
      for (var key in a) {
        if (_.has(a, key)) {
          // Count the expected number of properties.
          size++; // Deep compare each member.

          if (!(result = _.has(b, key) && eq(a[key], b[key], aStack, bStack))) break;
        }
      } // Ensure that both objects contain the same number of properties.


      if (result) {
        for (key in b) {
          if (_.has(b, key) && !size--) break;
        }

        result = !size;
      }
    } // Remove the first object from the stack of traversed objects.


    aStack.pop();
    bStack.pop();
    return result;
  }; // Perform a deep comparison to check if two objects are equal.


  _.isEqual = function (a, b) {
    return eq(a, b, [], []);
  }; // Is a given array, string, or object empty?
  // An "empty" object has no enumerable own-properties.


  _.isEmpty = function (obj) {
    if (obj == null) return true;
    if (_.isArray(obj) || _.isString(obj)) return obj.length === 0;

    for (var key in obj) {
      if (_.has(obj, key)) return false;
    }

    return true;
  }; // Is a given value a DOM element?


  _.isElement = function (obj) {
    return !!(obj && obj.nodeType === 1);
  }; // Is a given value an array?
  // Delegates to ECMA5's native Array.isArray


  _.isArray = nativeIsArray || function (obj) {
    return toString.call(obj) == '[object Array]';
  }; // Is a given variable an object?


  _.isObject = function (obj) {
    return obj === Object(obj);
  }; // Add some isType methods: isArguments, isFunction, isString, isNumber, isDate, isRegExp.


  each(['Arguments', 'Function', 'String', 'Number', 'Date', 'RegExp'], function (name) {
    _['is' + name] = function (obj) {
      return toString.call(obj) == '[object ' + name + ']';
    };
  }); // Define a fallback version of the method in browsers (ahem, IE), where
  // there isn't any inspectable "Arguments" type.

  if (!_.isArguments(arguments)) {
    _.isArguments = function (obj) {
      return !!(obj && _.has(obj, 'callee'));
    };
  } // Optimize `isFunction` if appropriate.


  if (true) {
    _.isFunction = function (obj) {
      return typeof obj === 'function';
    };
  } // Is a given object a finite number?


  _.isFinite = function (obj) {
    return isFinite(obj) && !isNaN(parseFloat(obj));
  }; // Is the given value `NaN`? (NaN is the only number which does not equal itself).


  _.isNaN = function (obj) {
    return _.isNumber(obj) && obj != +obj;
  }; // Is a given value a boolean?


  _.isBoolean = function (obj) {
    return obj === true || obj === false || toString.call(obj) == '[object Boolean]';
  }; // Is a given value equal to null?


  _.isNull = function (obj) {
    return obj === null;
  }; // Is a given variable undefined?


  _.isUndefined = function (obj) {
    return obj === void 0;
  }; // Shortcut function for checking if an object has a given property directly
  // on itself (in other words, not on a prototype).


  _.has = function (obj, key) {
    return hasOwnProperty.call(obj, key);
  }; // Utility Functions
  // -----------------
  // Run Underscore.js in *noConflict* mode, returning the `_` variable to its
  // previous owner. Returns a reference to the Underscore object.


  _.noConflict = function () {
    root._ = previousUnderscore;
    return this;
  }; // Keep the identity function around for default iterators.


  _.identity = function (value) {
    return value;
  };

  _.constant = function (value) {
    return function () {
      return value;
    };
  };

  _.property = function (key) {
    return function (obj) {
      return obj[key];
    };
  }; // Returns a predicate for checking whether an object has a given set of `key:value` pairs.


  _.matches = function (attrs) {
    return function (obj) {
      if (obj === attrs) return true; //avoid comparing an object to itself.

      for (var key in attrs) {
        if (attrs[key] !== obj[key]) return false;
      }

      return true;
    };
  }; // Run a function **n** times.


  _.times = function (n, iterator, context) {
    var accum = Array(Math.max(0, n));

    for (var i = 0; i < n; i++) {
      accum[i] = iterator.call(context, i);
    }

    return accum;
  }; // Return a random integer between min and max (inclusive).


  _.random = function (min, max) {
    if (max == null) {
      max = min;
      min = 0;
    }

    return min + Math.floor(Math.random() * (max - min + 1));
  }; // A (possibly faster) way to get the current timestamp as an integer.


  _.now = Date.now || function () {
    return new Date().getTime();
  }; // List of HTML entities for escaping.


  var entityMap = {
    escape: {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;'
    }
  };
  entityMap.unescape = _.invert(entityMap.escape); // Regexes containing the keys and values listed immediately above.

  var entityRegexes = {
    escape: new RegExp('[' + _.keys(entityMap.escape).join('') + ']', 'g'),
    unescape: new RegExp('(' + _.keys(entityMap.unescape).join('|') + ')', 'g')
  }; // Functions for escaping and unescaping strings to/from HTML interpolation.

  _.each(['escape', 'unescape'], function (method) {
    _[method] = function (string) {
      if (string == null) return '';
      return ('' + string).replace(entityRegexes[method], function (match) {
        return entityMap[method][match];
      });
    };
  }); // If the value of the named `property` is a function then invoke it with the
  // `object` as context; otherwise, return it.


  _.result = function (object, property) {
    if (object == null) return void 0;
    var value = object[property];
    return _.isFunction(value) ? value.call(object) : value;
  }; // Add your own custom functions to the Underscore object.


  _.mixin = function (obj) {
    each(_.functions(obj), function (name) {
      var func = _[name] = obj[name];

      _.prototype[name] = function () {
        var args = [this._wrapped];
        push.apply(args, arguments);
        return result.call(this, func.apply(_, args));
      };
    });
  }; // Generate a unique integer id (unique within the entire client session).
  // Useful for temporary DOM ids.


  var idCounter = 0;

  _.uniqueId = function (prefix) {
    var id = ++idCounter + '';
    return prefix ? prefix + id : id;
  }; // By default, Underscore uses ERB-style template delimiters, change the
  // following template settings to use alternative delimiters.


  _.templateSettings = {
    evaluate: /<%([\s\S]+?)%>/g,
    interpolate: /<%=([\s\S]+?)%>/g,
    escape: /<%-([\s\S]+?)%>/g
  }; // When customizing `templateSettings`, if you don't want to define an
  // interpolation, evaluation or escaping regex, we need one that is
  // guaranteed not to match.

  var noMatch = /(.)^/; // Certain characters need to be escaped so that they can be put into a
  // string literal.

  var escapes = {
    "'": "'",
    '\\': '\\',
    '\r': 'r',
    '\n': 'n',
    '\t': 't',
    "\u2028": 'u2028',
    "\u2029": 'u2029'
  };
  var escaper = /\\|'|\r|\n|\t|\u2028|\u2029/g; // JavaScript micro-templating, similar to John Resig's implementation.
  // Underscore templating handles arbitrary delimiters, preserves whitespace,
  // and correctly escapes quotes within interpolated code.

  _.template = function (text, data, settings) {
    var render;
    settings = _.defaults({}, settings, _.templateSettings); // Combine delimiters into one regular expression via alternation.

    var matcher = new RegExp([(settings.escape || noMatch).source, (settings.interpolate || noMatch).source, (settings.evaluate || noMatch).source].join('|') + '|$', 'g'); // Compile the template source, escaping string literals appropriately.

    var index = 0;
    var source = "__p+='";
    text.replace(matcher, function (match, escape, interpolate, evaluate, offset) {
      source += text.slice(index, offset).replace(escaper, function (match) {
        return '\\' + escapes[match];
      });

      if (escape) {
        source += "'+\n((__t=(" + escape + "))==null?'':_.escape(__t))+\n'";
      }

      if (interpolate) {
        source += "'+\n((__t=(" + interpolate + "))==null?'':__t)+\n'";
      }

      if (evaluate) {
        source += "';\n" + evaluate + "\n__p+='";
      }

      index = offset + match.length;
      return match;
    });
    source += "';\n"; // If a variable is not specified, place data values in local scope.

    if (!settings.variable) source = 'with(obj||{}){\n' + source + '}\n';
    source = "var __t,__p='',__j=Array.prototype.join," + "print=function(){__p+=__j.call(arguments,'');};\n" + source + "return __p;\n";

    try {
      render = new Function(settings.variable || 'obj', '_', source);
    } catch (e) {
      e.source = source;
      throw e;
    }

    if (data) return render(data, _);

    var template = function template(data) {
      return render.call(this, data, _);
    }; // Provide the compiled function source as a convenience for precompilation.


    template.source = 'function(' + (settings.variable || 'obj') + '){\n' + source + '}';
    return template;
  }; // Add a "chain" function, which will delegate to the wrapper.


  _.chain = function (obj) {
    return _(obj).chain();
  }; // OOP
  // ---------------
  // If Underscore is called as a function, it returns a wrapped object that
  // can be used OO-style. This wrapper holds altered versions of all the
  // underscore functions. Wrapped objects may be chained.
  // Helper function to continue chaining intermediate results.


  var result = function result(obj) {
    return this._chain ? _(obj).chain() : obj;
  }; // Add all of the Underscore functions to the wrapper object.


  _.mixin(_); // Add all mutator Array functions to the wrapper.


  each(['pop', 'push', 'reverse', 'shift', 'sort', 'splice', 'unshift'], function (name) {
    var method = ArrayProto[name];

    _.prototype[name] = function () {
      var obj = this._wrapped;
      method.apply(obj, arguments);
      if ((name == 'shift' || name == 'splice') && obj.length === 0) delete obj[0];
      return result.call(this, obj);
    };
  }); // Add all accessor Array functions to the wrapper.

  each(['concat', 'join', 'slice'], function (name) {
    var method = ArrayProto[name];

    _.prototype[name] = function () {
      return result.call(this, method.apply(this._wrapped, arguments));
    };
  });

  _.extend(_.prototype, {
    // Start chaining a wrapped Underscore object.
    chain: function chain() {
      this._chain = true;
      return this;
    },
    // Extracts the result from a wrapped and chained object.
    value: function value() {
      return this._wrapped;
    }
  }); // NOTE: this file has been patched so that Underscore defines itself as an
  // anonymous AMD module.  This allows us to create a wrapper module called "underscore"
  // that adds mixin functionality and enforces no-conflict mode.


  if (true) {
    !(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = (function () {
      return _;
    }).apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__),
				__WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
  }
}).call(this);

/***/ }),

/***/ 38:
/***/ (function(module, exports) {

module.exports = function(module) {
	if (!module.webpackPolyfill) {
		module.deprecate = function() {};
		module.paths = [];
		// module.parent = undefined by default
		if (!module.children) module.children = [];
		Object.defineProperty(module, "loaded", {
			enumerable: true,
			get: function() {
				return module.l;
			}
		});
		Object.defineProperty(module, "id", {
			enumerable: true,
			get: function() {
				return module.i;
			}
		});
		module.webpackPolyfill = 1;
	}
	return module;
};


/***/ }),

/***/ 41:
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
// ESM COMPAT FLAG
__webpack_require__.r(__webpack_exports__);

// EXTERNAL MODULE: external "react"
var external_react_ = __webpack_require__(0);
var external_react_default = /*#__PURE__*/__webpack_require__.n(external_react_);

// EXTERNAL MODULE: external "@splunk/react-ui/WaitSpinner"
var WaitSpinner_ = __webpack_require__(19);
var WaitSpinner_default = /*#__PURE__*/__webpack_require__.n(WaitSpinner_);

// EXTERNAL MODULE: external "@splunk/react-ui/Heading"
var Heading_ = __webpack_require__(12);
var Heading_default = /*#__PURE__*/__webpack_require__.n(Heading_);

// EXTERNAL MODULE: ./src/contrib/jquery-3.5.0.min.js
var jquery_3_5_0_min = __webpack_require__(36);
var jquery_3_5_0_min_default = /*#__PURE__*/__webpack_require__.n(jquery_3_5_0_min);

// EXTERNAL MODULE: ./src/contrib/underscore.js
var underscore = __webpack_require__(37);
var underscore_default = /*#__PURE__*/__webpack_require__.n(underscore);

// CONCATENATED MODULE: ./src/contrib/d3/d3.v3.js
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

var d3_v3_d3 = function () {
  var d3 = {
    version: "3.1.4"
  };
  if (!Date.now) Date.now = function () {
    return +new Date();
  };
  var d3_document = document,
      d3_window = window;

  try {
    d3_document.createElement("div").style.setProperty("opacity", 0, "");
  } catch (error) {
    var d3_style_prototype = d3_window.CSSStyleDeclaration.prototype,
        d3_style_setProperty = d3_style_prototype.setProperty;

    d3_style_prototype.setProperty = function (name, value, priority) {
      d3_style_setProperty.call(this, name, value + "", priority);
    };
  }

  d3.ascending = function (a, b) {
    return a < b ? -1 : a > b ? 1 : a >= b ? 0 : NaN;
  };

  d3.descending = function (a, b) {
    return b < a ? -1 : b > a ? 1 : b >= a ? 0 : NaN;
  };

  d3.min = function (array, f) {
    var i = -1,
        n = array.length,
        a,
        b;

    if (arguments.length === 1) {
      while (++i < n && ((a = array[i]) == null || a != a)) {
        a = undefined;
      }

      while (++i < n) {
        if ((b = array[i]) != null && a > b) a = b;
      }
    } else {
      while (++i < n && ((a = f.call(array, array[i], i)) == null || a != a)) {
        a = undefined;
      }

      while (++i < n) {
        if ((b = f.call(array, array[i], i)) != null && a > b) a = b;
      }
    }

    return a;
  };

  d3.max = function (array, f) {
    var i = -1,
        n = array.length,
        a,
        b;

    if (arguments.length === 1) {
      while (++i < n && ((a = array[i]) == null || a != a)) {
        a = undefined;
      }

      while (++i < n) {
        if ((b = array[i]) != null && b > a) a = b;
      }
    } else {
      while (++i < n && ((a = f.call(array, array[i], i)) == null || a != a)) {
        a = undefined;
      }

      while (++i < n) {
        if ((b = f.call(array, array[i], i)) != null && b > a) a = b;
      }
    }

    return a;
  };

  d3.extent = function (array, f) {
    var i = -1,
        n = array.length,
        a,
        b,
        c;

    if (arguments.length === 1) {
      while (++i < n && ((a = c = array[i]) == null || a != a)) {
        a = c = undefined;
      }

      while (++i < n) {
        if ((b = array[i]) != null) {
          if (a > b) a = b;
          if (c < b) c = b;
        }
      }
    } else {
      while (++i < n && ((a = c = f.call(array, array[i], i)) == null || a != a)) {
        a = undefined;
      }

      while (++i < n) {
        if ((b = f.call(array, array[i], i)) != null) {
          if (a > b) a = b;
          if (c < b) c = b;
        }
      }
    }

    return [a, c];
  };

  d3.sum = function (array, f) {
    var s = 0,
        n = array.length,
        a,
        i = -1;

    if (arguments.length === 1) {
      while (++i < n) {
        if (!isNaN(a = +array[i])) s += a;
      }
    } else {
      while (++i < n) {
        if (!isNaN(a = +f.call(array, array[i], i))) s += a;
      }
    }

    return s;
  };

  function d3_number(x) {
    return x != null && !isNaN(x);
  }

  d3.mean = function (array, f) {
    var n = array.length,
        a,
        m = 0,
        i = -1,
        j = 0;

    if (arguments.length === 1) {
      while (++i < n) {
        if (d3_number(a = array[i])) m += (a - m) / ++j;
      }
    } else {
      while (++i < n) {
        if (d3_number(a = f.call(array, array[i], i))) m += (a - m) / ++j;
      }
    }

    return j ? m : undefined;
  };

  d3.quantile = function (values, p) {
    var H = (values.length - 1) * p + 1,
        h = Math.floor(H),
        v = +values[h - 1],
        e = H - h;
    return e ? v + e * (values[h] - v) : v;
  };

  d3.median = function (array, f) {
    if (arguments.length > 1) array = array.map(f);
    array = array.filter(d3_number);
    return array.length ? d3.quantile(array.sort(d3.ascending), .5) : undefined;
  };

  d3.bisector = function (f) {
    return {
      left: function left(a, x, lo, hi) {
        if (arguments.length < 3) lo = 0;
        if (arguments.length < 4) hi = a.length;

        while (lo < hi) {
          var mid = lo + hi >>> 1;
          if (f.call(a, a[mid], mid) < x) lo = mid + 1;else hi = mid;
        }

        return lo;
      },
      right: function right(a, x, lo, hi) {
        if (arguments.length < 3) lo = 0;
        if (arguments.length < 4) hi = a.length;

        while (lo < hi) {
          var mid = lo + hi >>> 1;
          if (x < f.call(a, a[mid], mid)) hi = mid;else lo = mid + 1;
        }

        return lo;
      }
    };
  };

  var d3_bisector = d3.bisector(function (d) {
    return d;
  });
  d3.bisectLeft = d3_bisector.left;
  d3.bisect = d3.bisectRight = d3_bisector.right;

  d3.shuffle = function (array) {
    var m = array.length,
        t,
        i;

    while (m) {
      i = Math.random() * m-- | 0;
      t = array[m], array[m] = array[i], array[i] = t;
    }

    return array;
  };

  d3.permute = function (array, indexes) {
    var permutes = [],
        i = -1,
        n = indexes.length;

    while (++i < n) {
      permutes[i] = array[indexes[i]];
    }

    return permutes;
  };

  d3.zip = function () {
    if (!(n = arguments.length)) return [];

    for (var i = -1, m = d3.min(arguments, d3_zipLength), zips = new Array(m); ++i < m;) {
      for (var j = -1, n, zip = zips[i] = new Array(n); ++j < n;) {
        zip[j] = arguments[j][i];
      }
    }

    return zips;
  };

  function d3_zipLength(d) {
    return d.length;
  }

  d3.transpose = function (matrix) {
    return d3.zip.apply(d3, matrix);
  };

  d3.keys = function (map) {
    var keys = [];

    for (var key in map) {
      keys.push(key);
    }

    return keys;
  };

  d3.values = function (map) {
    var values = [];

    for (var key in map) {
      values.push(map[key]);
    }

    return values;
  };

  d3.entries = function (map) {
    var entries = [];

    for (var key in map) {
      entries.push({
        key: key,
        value: map[key]
      });
    }

    return entries;
  };

  d3.merge = function (arrays) {
    return Array.prototype.concat.apply([], arrays);
  };

  d3.range = function (start, stop, step) {
    if (arguments.length < 3) {
      step = 1;

      if (arguments.length < 2) {
        stop = start;
        start = 0;
      }
    }

    if ((stop - start) / step === Infinity) throw new Error("infinite range");
    var range = [],
        k = d3_range_integerScale(Math.abs(step)),
        i = -1,
        j;
    start *= k, stop *= k, step *= k;
    if (step < 0) while ((j = start + step * ++i) > stop) {
      range.push(j / k);
    } else while ((j = start + step * ++i) < stop) {
      range.push(j / k);
    }
    return range;
  };

  function d3_range_integerScale(x) {
    var k = 1;

    while (x * k % 1) {
      k *= 10;
    }

    return k;
  }

  function d3_class(ctor, properties) {
    try {
      for (var key in properties) {
        Object.defineProperty(ctor.prototype, key, {
          value: properties[key],
          enumerable: false
        });
      }
    } catch (e) {
      ctor.prototype = properties;
    }
  }

  d3.map = function (object) {
    var map = new d3_Map();

    for (var key in object) {
      map.set(key, object[key]);
    }

    return map;
  };

  function d3_Map() {}

  d3_class(d3_Map, {
    has: function has(key) {
      return d3_map_prefix + key in this;
    },
    get: function get(key) {
      return this[d3_map_prefix + key];
    },
    set: function set(key, value) {
      return this[d3_map_prefix + key] = value;
    },
    remove: function remove(key) {
      key = d3_map_prefix + key;
      return key in this && delete this[key];
    },
    keys: function keys() {
      var keys = [];
      this.forEach(function (key) {
        keys.push(key);
      });
      return keys;
    },
    values: function values() {
      var values = [];
      this.forEach(function (key, value) {
        values.push(value);
      });
      return values;
    },
    entries: function entries() {
      var entries = [];
      this.forEach(function (key, value) {
        entries.push({
          key: key,
          value: value
        });
      });
      return entries;
    },
    forEach: function forEach(f) {
      for (var key in this) {
        if (key.charCodeAt(0) === d3_map_prefixCode) {
          f.call(this, key.substring(1), this[key]);
        }
      }
    }
  });
  var d3_map_prefix = "\0",
      d3_map_prefixCode = d3_map_prefix.charCodeAt(0);

  d3.nest = function () {
    var nest = {},
        keys = [],
        sortKeys = [],
        sortValues,
        rollup;

    function map(mapType, array, depth) {
      if (depth >= keys.length) return rollup ? rollup.call(nest, array) : sortValues ? array.sort(sortValues) : array;
      var i = -1,
          n = array.length,
          key = keys[depth++],
          keyValue,
          object,
          setter,
          valuesByKey = new d3_Map(),
          values;

      while (++i < n) {
        if (values = valuesByKey.get(keyValue = key(object = array[i]))) {
          values.push(object);
        } else {
          valuesByKey.set(keyValue, [object]);
        }
      }

      if (mapType) {
        object = mapType();

        setter = function setter(keyValue, values) {
          object.set(keyValue, map(mapType, values, depth));
        };
      } else {
        object = {};

        setter = function setter(keyValue, values) {
          object[keyValue] = map(mapType, values, depth);
        };
      }

      valuesByKey.forEach(setter);
      return object;
    }

    function entries(map, depth) {
      if (depth >= keys.length) return map;
      var array = [],
          sortKey = sortKeys[depth++];
      map.forEach(function (key, keyMap) {
        array.push({
          key: key,
          values: entries(keyMap, depth)
        });
      });
      return sortKey ? array.sort(function (a, b) {
        return sortKey(a.key, b.key);
      }) : array;
    }

    nest.map = function (array, mapType) {
      return map(mapType, array, 0);
    };

    nest.entries = function (array) {
      return entries(map(d3.map, array, 0), 0);
    };

    nest.key = function (d) {
      keys.push(d);
      return nest;
    };

    nest.sortKeys = function (order) {
      sortKeys[keys.length - 1] = order;
      return nest;
    };

    nest.sortValues = function (order) {
      sortValues = order;
      return nest;
    };

    nest.rollup = function (f) {
      rollup = f;
      return nest;
    };

    return nest;
  };

  d3.set = function (array) {
    var set = new d3_Set();
    if (array) for (var i = 0; i < array.length; i++) {
      set.add(array[i]);
    }
    return set;
  };

  function d3_Set() {}

  d3_class(d3_Set, {
    has: function has(value) {
      return d3_map_prefix + value in this;
    },
    add: function add(value) {
      this[d3_map_prefix + value] = true;
      return value;
    },
    remove: function remove(value) {
      value = d3_map_prefix + value;
      return value in this && delete this[value];
    },
    values: function values() {
      var values = [];
      this.forEach(function (value) {
        values.push(value);
      });
      return values;
    },
    forEach: function forEach(f) {
      for (var value in this) {
        if (value.charCodeAt(0) === d3_map_prefixCode) {
          f.call(this, value.substring(1));
        }
      }
    }
  });
  d3.behavior = {};

  d3.rebind = function (target, source) {
    var i = 1,
        n = arguments.length,
        method;

    while (++i < n) {
      target[method = arguments[i]] = d3_rebind(target, source, source[method]);
    }

    return target;
  };

  function d3_rebind(target, source, method) {
    return function () {
      var value = method.apply(source, arguments);
      return value === source ? target : value;
    };
  }

  d3.dispatch = function () {
    var dispatch = new d3_dispatch(),
        i = -1,
        n = arguments.length;

    while (++i < n) {
      dispatch[arguments[i]] = d3_dispatch_event(dispatch);
    }

    return dispatch;
  };

  function d3_dispatch() {}

  d3_dispatch.prototype.on = function (type, listener) {
    var i = type.indexOf("."),
        name = "";

    if (i >= 0) {
      name = type.substring(i + 1);
      type = type.substring(0, i);
    }

    if (type) return arguments.length < 2 ? this[type].on(name) : this[type].on(name, listener);

    if (arguments.length === 2) {
      if (listener == null) for (type in this) {
        if (this.hasOwnProperty(type)) this[type].on(name, null);
      }
      return this;
    }
  };

  function d3_dispatch_event(dispatch) {
    var listeners = [],
        listenerByName = new d3_Map();

    function event() {
      var z = listeners,
          i = -1,
          n = z.length,
          l;

      while (++i < n) {
        if (l = z[i].on) l.apply(this, arguments);
      }

      return dispatch;
    }

    event.on = function (name, listener) {
      var l = listenerByName.get(name),
          i;
      if (arguments.length < 2) return l && l.on;

      if (l) {
        l.on = null;
        listeners = listeners.slice(0, i = listeners.indexOf(l)).concat(listeners.slice(i + 1));
        listenerByName.remove(name);
      }

      if (listener) listeners.push(listenerByName.set(name, {
        on: listener
      }));
      return dispatch;
    };

    return event;
  }

  d3.event = null;

  function d3_eventCancel() {
    d3.event.stopPropagation();
    d3.event.preventDefault();
  }

  function d3_eventSource() {
    var e = d3.event,
        s;

    while (s = e.sourceEvent) {
      e = s;
    }

    return e;
  }

  function d3_eventDispatch(target) {
    var dispatch = new d3_dispatch(),
        i = 0,
        n = arguments.length;

    while (++i < n) {
      dispatch[arguments[i]] = d3_dispatch_event(dispatch);
    }

    dispatch.of = function (thiz, argumentz) {
      return function (e1) {
        try {
          var e0 = e1.sourceEvent = d3.event;
          e1.target = target;
          d3.event = e1;
          dispatch[e1.type].apply(thiz, argumentz);
        } finally {
          d3.event = e0;
        }
      };
    };

    return dispatch;
  }

  d3.mouse = function (container) {
    return d3_mousePoint(container, d3_eventSource());
  };

  var d3_mouse_bug44083 = /WebKit/.test(d3_window.navigator.userAgent) ? -1 : 0;

  function d3_mousePoint(container, e) {
    var svg = container.ownerSVGElement || container;

    if (svg.createSVGPoint) {
      var point = svg.createSVGPoint();

      if (d3_mouse_bug44083 < 0 && (d3_window.scrollX || d3_window.scrollY)) {
        svg = d3.select(d3_document.body).append("svg").style("position", "absolute").style("top", 0).style("left", 0);
        var ctm = svg[0][0].getScreenCTM();
        d3_mouse_bug44083 = !(ctm.f || ctm.e);
        svg.remove();
      }

      if (d3_mouse_bug44083) {
        point.x = e.pageX;
        point.y = e.pageY;
      } else {
        point.x = e.clientX;
        point.y = e.clientY;
      }

      point = point.matrixTransform(container.getScreenCTM().inverse());
      return [point.x, point.y];
    }

    var rect = container.getBoundingClientRect();
    return [e.clientX - rect.left - container.clientLeft, e.clientY - rect.top - container.clientTop];
  }

  var d3_array = d3_arraySlice;

  function d3_arrayCopy(pseudoarray) {
    var i = -1,
        n = pseudoarray.length,
        array = [];

    while (++i < n) {
      array.push(pseudoarray[i]);
    }

    return array;
  }

  function d3_arraySlice(pseudoarray) {
    return Array.prototype.slice.call(pseudoarray);
  }

  try {
    d3_array(d3_document.documentElement.childNodes)[0].nodeType;
  } catch (e) {
    d3_array = d3_arrayCopy;
  }

  var d3_arraySubclass = [].__proto__ ? function (array, prototype) {
    array.__proto__ = prototype;
  } : function (array, prototype) {
    for (var property in prototype) {
      array[property] = prototype[property];
    }
  };

  d3.touches = function (container, touches) {
    if (arguments.length < 2) touches = d3_eventSource().touches;
    return touches ? d3_array(touches).map(function (touch) {
      var point = d3_mousePoint(container, touch);
      point.identifier = touch.identifier;
      return point;
    }) : [];
  };

  d3.behavior.drag = function () {
    var event = d3_eventDispatch(drag, "drag", "dragstart", "dragend"),
        origin = null;

    function drag() {
      this.on("mousedown.drag", mousedown).on("touchstart.drag", mousedown);
    }

    function mousedown() {
      var target = this,
          event_ = event.of(target, arguments),
          eventTarget = d3.event.target,
          touchId = d3.event.touches ? d3.event.changedTouches[0].identifier : null,
          offset,
          origin_ = point(),
          moved = 0;
      var w = d3.select(d3_window).on(touchId != null ? "touchmove.drag-" + touchId : "mousemove.drag", dragmove).on(touchId != null ? "touchend.drag-" + touchId : "mouseup.drag", dragend, true);

      if (origin) {
        offset = origin.apply(target, arguments);
        offset = [offset.x - origin_[0], offset.y - origin_[1]];
      } else {
        offset = [0, 0];
      }

      if (touchId == null) d3_eventCancel();
      event_({
        type: "dragstart"
      });

      function point() {
        var p = target.parentNode;
        return touchId != null ? d3.touches(p).filter(function (p) {
          return p.identifier === touchId;
        })[0] : d3.mouse(p);
      }

      function dragmove() {
        if (!target.parentNode) return dragend();
        var p = point(),
            dx = p[0] - origin_[0],
            dy = p[1] - origin_[1];
        moved |= dx | dy;
        origin_ = p;
        d3_eventCancel();
        event_({
          type: "drag",
          x: p[0] + offset[0],
          y: p[1] + offset[1],
          dx: dx,
          dy: dy
        });
      }

      function dragend() {
        event_({
          type: "dragend"
        });

        if (moved) {
          d3_eventCancel();
          if (d3.event.target === eventTarget) w.on("click.drag", click, true);
        }

        w.on(touchId != null ? "touchmove.drag-" + touchId : "mousemove.drag", null).on(touchId != null ? "touchend.drag-" + touchId : "mouseup.drag", null);
      }

      function click() {
        d3_eventCancel();
        w.on("click.drag", null);
      }
    }

    drag.origin = function (x) {
      if (!arguments.length) return origin;
      origin = x;
      return drag;
    };

    return d3.rebind(drag, event, "on");
  };

  function d3_selection(groups) {
    d3_arraySubclass(groups, d3_selectionPrototype);
    return groups;
  }

  var d3_select = function d3_select(s, n) {
    return n.querySelector(s);
  },
      d3_selectAll = function d3_selectAll(s, n) {
    return n.querySelectorAll(s);
  },
      d3_selectRoot = d3_document.documentElement,
      d3_selectMatcher = d3_selectRoot.matchesSelector || d3_selectRoot.webkitMatchesSelector || d3_selectRoot.mozMatchesSelector || d3_selectRoot.msMatchesSelector || d3_selectRoot.oMatchesSelector,
      d3_selectMatches = function d3_selectMatches(n, s) {
    return d3_selectMatcher.call(n, s);
  };

  if (typeof Sizzle === "function") {
    d3_select = function d3_select(s, n) {
      return Sizzle(s, n)[0] || null;
    };

    d3_selectAll = function d3_selectAll(s, n) {
      return Sizzle.uniqueSort(Sizzle(s, n));
    };

    d3_selectMatches = Sizzle.matchesSelector;
  }

  var d3_selectionPrototype = [];

  d3.selection = function () {
    return d3_selectionRoot;
  };

  d3.selection.prototype = d3_selectionPrototype;

  d3_selectionPrototype.select = function (selector) {
    var subgroups = [],
        subgroup,
        subnode,
        group,
        node;
    if (typeof selector !== "function") selector = d3_selection_selector(selector);

    for (var j = -1, m = this.length; ++j < m;) {
      subgroups.push(subgroup = []);
      subgroup.parentNode = (group = this[j]).parentNode;

      for (var i = -1, n = group.length; ++i < n;) {
        if (node = group[i]) {
          subgroup.push(subnode = selector.call(node, node.__data__, i));
          if (subnode && "__data__" in node) subnode.__data__ = node.__data__;
        } else {
          subgroup.push(null);
        }
      }
    }

    return d3_selection(subgroups);
  };

  function d3_selection_selector(selector) {
    return function () {
      return d3_select(selector, this);
    };
  }

  d3_selectionPrototype.selectAll = function (selector) {
    var subgroups = [],
        subgroup,
        node;
    if (typeof selector !== "function") selector = d3_selection_selectorAll(selector);

    for (var j = -1, m = this.length; ++j < m;) {
      for (var group = this[j], i = -1, n = group.length; ++i < n;) {
        if (node = group[i]) {
          subgroups.push(subgroup = d3_array(selector.call(node, node.__data__, i)));
          subgroup.parentNode = node;
        }
      }
    }

    return d3_selection(subgroups);
  };

  function d3_selection_selectorAll(selector) {
    return function () {
      return d3_selectAll(selector, this);
    };
  }

  var d3_nsPrefix = {
    svg: "http://www.w3.org/2000/svg",
    xhtml: "http://www.w3.org/1999/xhtml",
    xlink: "http://www.w3.org/1999/xlink",
    xml: "http://www.w3.org/XML/1998/namespace",
    xmlns: "http://www.w3.org/2000/xmlns/"
  };
  d3.ns = {
    prefix: d3_nsPrefix,
    qualify: function qualify(name) {
      var i = name.indexOf(":"),
          prefix = name;

      if (i >= 0) {
        prefix = name.substring(0, i);
        name = name.substring(i + 1);
      }

      return d3_nsPrefix.hasOwnProperty(prefix) ? {
        space: d3_nsPrefix[prefix],
        local: name
      } : name;
    }
  };

  d3_selectionPrototype.attr = function (name, value) {
    if (arguments.length < 2) {
      if (typeof name === "string") {
        var node = this.node();
        name = d3.ns.qualify(name);
        return name.local ? node.getAttributeNS(name.space, name.local) : node.getAttribute(name);
      }

      for (value in name) {
        this.each(d3_selection_attr(value, name[value]));
      }

      return this;
    }

    return this.each(d3_selection_attr(name, value));
  };

  function d3_selection_attr(name, value) {
    name = d3.ns.qualify(name);

    function attrNull() {
      this.removeAttribute(name);
    }

    function attrNullNS() {
      this.removeAttributeNS(name.space, name.local);
    }

    function attrConstant() {
      this.setAttribute(name, value);
    }

    function attrConstantNS() {
      this.setAttributeNS(name.space, name.local, value);
    }

    function attrFunction() {
      var x = value.apply(this, arguments);
      if (x == null) this.removeAttribute(name);else this.setAttribute(name, x);
    }

    function attrFunctionNS() {
      var x = value.apply(this, arguments);
      if (x == null) this.removeAttributeNS(name.space, name.local);else this.setAttributeNS(name.space, name.local, x);
    }

    return value == null ? name.local ? attrNullNS : attrNull : typeof value === "function" ? name.local ? attrFunctionNS : attrFunction : name.local ? attrConstantNS : attrConstant;
  }

  function d3_collapse(s) {
    return s.trim().replace(/\s+/g, " ");
  }

  d3.requote = function (s) {
    return s.replace(d3_requote_re, "\\$&");
  };

  var d3_requote_re = /[\\\^\$\*\+\?\|\[\]\(\)\.\{\}]/g;

  d3_selectionPrototype.classed = function (name, value) {
    if (arguments.length < 2) {
      if (typeof name === "string") {
        var node = this.node(),
            n = (name = name.trim().split(/^|\s+/g)).length,
            i = -1;

        if (value = node.classList) {
          while (++i < n) {
            if (!value.contains(name[i])) return false;
          }
        } else {
          value = node.getAttribute("class");

          while (++i < n) {
            if (!d3_selection_classedRe(name[i]).test(value)) return false;
          }
        }

        return true;
      }

      for (value in name) {
        this.each(d3_selection_classed(value, name[value]));
      }

      return this;
    }

    return this.each(d3_selection_classed(name, value));
  };

  function d3_selection_classedRe(name) {
    return new RegExp("(?:^|\\s+)" + d3.requote(name) + "(?:\\s+|$)", "g");
  }

  function d3_selection_classed(name, value) {
    name = name.trim().split(/\s+/).map(d3_selection_classedName);
    var n = name.length;

    function classedConstant() {
      var i = -1;

      while (++i < n) {
        name[i](this, value);
      }
    }

    function classedFunction() {
      var i = -1,
          x = value.apply(this, arguments);

      while (++i < n) {
        name[i](this, x);
      }
    }

    return typeof value === "function" ? classedFunction : classedConstant;
  }

  function d3_selection_classedName(name) {
    var re = d3_selection_classedRe(name);
    return function (node, value) {
      if (c = node.classList) return value ? c.add(name) : c.remove(name);
      var c = node.getAttribute("class") || "";

      if (value) {
        re.lastIndex = 0;
        if (!re.test(c)) node.setAttribute("class", d3_collapse(c + " " + name));
      } else {
        node.setAttribute("class", d3_collapse(c.replace(re, " ")));
      }
    };
  }

  d3_selectionPrototype.style = function (name, value, priority) {
    var n = arguments.length;

    if (n < 3) {
      if (typeof name !== "string") {
        if (n < 2) value = "";

        for (priority in name) {
          this.each(d3_selection_style(priority, name[priority], value));
        }

        return this;
      }

      if (n < 2) return d3_window.getComputedStyle(this.node(), null).getPropertyValue(name);
      priority = "";
    }

    return this.each(d3_selection_style(name, value, priority));
  };

  function d3_selection_style(name, value, priority) {
    function styleNull() {
      this.style.removeProperty(name);
    }

    function styleConstant() {
      this.style.setProperty(name, value, priority);
    }

    function styleFunction() {
      var x = value.apply(this, arguments);
      if (x == null) this.style.removeProperty(name);else this.style.setProperty(name, x, priority);
    }

    return value == null ? styleNull : typeof value === "function" ? styleFunction : styleConstant;
  }

  d3_selectionPrototype.property = function (name, value) {
    if (arguments.length < 2) {
      if (typeof name === "string") return this.node()[name];

      for (value in name) {
        this.each(d3_selection_property(value, name[value]));
      }

      return this;
    }

    return this.each(d3_selection_property(name, value));
  };

  function d3_selection_property(name, value) {
    function propertyNull() {
      delete this[name];
    }

    function propertyConstant() {
      this[name] = value;
    }

    function propertyFunction() {
      var x = value.apply(this, arguments);
      if (x == null) delete this[name];else this[name] = x;
    }

    return value == null ? propertyNull : typeof value === "function" ? propertyFunction : propertyConstant;
  }

  d3_selectionPrototype.text = function (value) {
    return arguments.length ? this.each(typeof value === "function" ? function () {
      var v = value.apply(this, arguments);
      this.textContent = v == null ? "" : v;
    } : value == null ? function () {
      this.textContent = "";
    } : function () {
      this.textContent = value;
    }) : this.node().textContent;
  };

  d3_selectionPrototype.html = function (value) {
    return arguments.length ? this.each(typeof value === "function" ? function () {
      var v = value.apply(this, arguments);
      this.innerHTML = v == null ? "" : v;
    } : value == null ? function () {
      this.innerHTML = "";
    } : function () {
      this.innerHTML = value;
    }) : this.node().innerHTML;
  };

  d3_selectionPrototype.append = function (name) {
    name = d3.ns.qualify(name);

    function append() {
      return this.appendChild(d3_document.createElementNS(this.namespaceURI, name));
    }

    function appendNS() {
      return this.appendChild(d3_document.createElementNS(name.space, name.local));
    }

    return this.select(name.local ? appendNS : append);
  };

  d3_selectionPrototype.insert = function (name, before) {
    name = d3.ns.qualify(name);
    if (typeof before !== "function") before = d3_selection_selector(before);

    function insert(d, i) {
      return this.insertBefore(d3_document.createElementNS(this.namespaceURI, name), before.call(this, d, i));
    }

    function insertNS(d, i) {
      return this.insertBefore(d3_document.createElementNS(name.space, name.local), before.call(this, d, i));
    }

    return this.select(name.local ? insertNS : insert);
  };

  d3_selectionPrototype.remove = function () {
    return this.each(function () {
      var parent = this.parentNode;
      if (parent) parent.removeChild(this);
    });
  };

  d3_selectionPrototype.data = function (value, key) {
    var i = -1,
        n = this.length,
        group,
        node;

    if (!arguments.length) {
      value = new Array(n = (group = this[0]).length);

      while (++i < n) {
        if (node = group[i]) {
          value[i] = node.__data__;
        }
      }

      return value;
    }

    function bind(group, groupData) {
      var i,
          n = group.length,
          m = groupData.length,
          n0 = Math.min(n, m),
          updateNodes = new Array(m),
          enterNodes = new Array(m),
          exitNodes = new Array(n),
          node,
          nodeData;

      if (key) {
        var nodeByKeyValue = new d3_Map(),
            dataByKeyValue = new d3_Map(),
            keyValues = [],
            keyValue;

        for (i = -1; ++i < n;) {
          keyValue = key.call(node = group[i], node.__data__, i);

          if (nodeByKeyValue.has(keyValue)) {
            exitNodes[i] = node;
          } else {
            nodeByKeyValue.set(keyValue, node);
          }

          keyValues.push(keyValue);
        }

        for (i = -1; ++i < m;) {
          keyValue = key.call(groupData, nodeData = groupData[i], i);

          if (node = nodeByKeyValue.get(keyValue)) {
            updateNodes[i] = node;
            node.__data__ = nodeData;
          } else if (!dataByKeyValue.has(keyValue)) {
            enterNodes[i] = d3_selection_dataNode(nodeData);
          }

          dataByKeyValue.set(keyValue, nodeData);
          nodeByKeyValue.remove(keyValue);
        }

        for (i = -1; ++i < n;) {
          if (nodeByKeyValue.has(keyValues[i])) {
            exitNodes[i] = group[i];
          }
        }
      } else {
        for (i = -1; ++i < n0;) {
          node = group[i];
          nodeData = groupData[i];

          if (node) {
            node.__data__ = nodeData;
            updateNodes[i] = node;
          } else {
            enterNodes[i] = d3_selection_dataNode(nodeData);
          }
        }

        for (; i < m; ++i) {
          enterNodes[i] = d3_selection_dataNode(groupData[i]);
        }

        for (; i < n; ++i) {
          exitNodes[i] = group[i];
        }
      }

      enterNodes.update = updateNodes;
      enterNodes.parentNode = updateNodes.parentNode = exitNodes.parentNode = group.parentNode;
      enter.push(enterNodes);
      update.push(updateNodes);
      exit.push(exitNodes);
    }

    var enter = d3_selection_enter([]),
        update = d3_selection([]),
        exit = d3_selection([]);

    if (typeof value === "function") {
      while (++i < n) {
        bind(group = this[i], value.call(group, group.parentNode.__data__, i));
      }
    } else {
      while (++i < n) {
        bind(group = this[i], value);
      }
    }

    update.enter = function () {
      return enter;
    };

    update.exit = function () {
      return exit;
    };

    return update;
  };

  function d3_selection_dataNode(data) {
    return {
      __data__: data
    };
  }

  d3_selectionPrototype.datum = function (value) {
    return arguments.length ? this.property("__data__", value) : this.property("__data__");
  };

  d3_selectionPrototype.filter = function (filter) {
    var subgroups = [],
        subgroup,
        group,
        node;
    if (typeof filter !== "function") filter = d3_selection_filter(filter);

    for (var j = 0, m = this.length; j < m; j++) {
      subgroups.push(subgroup = []);
      subgroup.parentNode = (group = this[j]).parentNode;

      for (var i = 0, n = group.length; i < n; i++) {
        if ((node = group[i]) && filter.call(node, node.__data__, i)) {
          subgroup.push(node);
        }
      }
    }

    return d3_selection(subgroups);
  };

  function d3_selection_filter(selector) {
    return function () {
      return d3_selectMatches(this, selector);
    };
  }

  d3_selectionPrototype.order = function () {
    for (var j = -1, m = this.length; ++j < m;) {
      for (var group = this[j], i = group.length - 1, next = group[i], node; --i >= 0;) {
        if (node = group[i]) {
          if (next && next !== node.nextSibling) next.parentNode.insertBefore(node, next);
          next = node;
        }
      }
    }

    return this;
  };

  d3_selectionPrototype.sort = function (comparator) {
    comparator = d3_selection_sortComparator.apply(this, arguments);

    for (var j = -1, m = this.length; ++j < m;) {
      this[j].sort(comparator);
    }

    return this.order();
  };

  function d3_selection_sortComparator(comparator) {
    if (!arguments.length) comparator = d3.ascending;
    return function (a, b) {
      return !a - !b || comparator(a.__data__, b.__data__);
    };
  }

  function d3_noop() {}

  d3_selectionPrototype.on = function (type, listener, capture) {
    var n = arguments.length;

    if (n < 3) {
      if (typeof type !== "string") {
        if (n < 2) listener = false;

        for (capture in type) {
          this.each(d3_selection_on(capture, type[capture], listener));
        }

        return this;
      }

      if (n < 2) return (n = this.node()["__on" + type]) && n._;
      capture = false;
    }

    return this.each(d3_selection_on(type, listener, capture));
  };

  function d3_selection_on(type, listener, capture) {
    var name = "__on" + type,
        i = type.indexOf("."),
        wrap = d3_selection_onListener;
    if (i > 0) type = type.substring(0, i);
    var filter = d3_selection_onFilters.get(type);
    if (filter) type = filter, wrap = d3_selection_onFilter;

    function onRemove() {
      var l = this[name];

      if (l) {
        this.removeEventListener(type, l, l.$);
        delete this[name];
      }
    }

    function onAdd() {
      var l = wrap(listener, d3_array(arguments));
      onRemove.call(this);
      this.addEventListener(type, this[name] = l, l.$ = capture);
      l._ = listener;
    }

    function removeAll() {
      var re = new RegExp("^__on([^.]+)" + d3.requote(type) + "$"),
          match;

      for (var name in this) {
        if (match = name.match(re)) {
          var l = this[name];
          this.removeEventListener(match[1], l, l.$);
          delete this[name];
        }
      }
    }

    return i ? listener ? onAdd : onRemove : listener ? d3_noop : removeAll;
  }

  var d3_selection_onFilters = d3.map({
    mouseenter: "mouseover",
    mouseleave: "mouseout"
  });
  d3_selection_onFilters.forEach(function (k) {
    if ("on" + k in d3_document) d3_selection_onFilters.remove(k);
  });

  function d3_selection_onListener(listener, argumentz) {
    return function (e) {
      var o = d3.event;
      d3.event = e;
      argumentz[0] = this.__data__;

      try {
        listener.apply(this, argumentz);
      } finally {
        d3.event = o;
      }
    };
  }

  function d3_selection_onFilter(listener, argumentz) {
    var l = d3_selection_onListener(listener, argumentz);
    return function (e) {
      var target = this,
          related = e.relatedTarget;

      if (!related || related !== target && !(related.compareDocumentPosition(target) & 8)) {
        l.call(target, e);
      }
    };
  }

  d3_selectionPrototype.each = function (callback) {
    return d3_selection_each(this, function (node, i, j) {
      callback.call(node, node.__data__, i, j);
    });
  };

  function d3_selection_each(groups, callback) {
    for (var j = 0, m = groups.length; j < m; j++) {
      for (var group = groups[j], i = 0, n = group.length, node; i < n; i++) {
        if (node = group[i]) callback(node, i, j);
      }
    }

    return groups;
  }

  d3_selectionPrototype.call = function (callback) {
    var args = d3_array(arguments);
    callback.apply(args[0] = this, args);
    return this;
  };

  d3_selectionPrototype.empty = function () {
    return !this.node();
  };

  d3_selectionPrototype.node = function () {
    for (var j = 0, m = this.length; j < m; j++) {
      for (var group = this[j], i = 0, n = group.length; i < n; i++) {
        var node = group[i];
        if (node) return node;
      }
    }

    return null;
  };

  function d3_selection_enter(selection) {
    d3_arraySubclass(selection, d3_selection_enterPrototype);
    return selection;
  }

  var d3_selection_enterPrototype = [];
  d3.selection.enter = d3_selection_enter;
  d3.selection.enter.prototype = d3_selection_enterPrototype;
  d3_selection_enterPrototype.append = d3_selectionPrototype.append;
  d3_selection_enterPrototype.insert = d3_selectionPrototype.insert;
  d3_selection_enterPrototype.empty = d3_selectionPrototype.empty;
  d3_selection_enterPrototype.node = d3_selectionPrototype.node;

  d3_selection_enterPrototype.select = function (selector) {
    var subgroups = [],
        subgroup,
        subnode,
        upgroup,
        group,
        node;

    for (var j = -1, m = this.length; ++j < m;) {
      upgroup = (group = this[j]).update;
      subgroups.push(subgroup = []);
      subgroup.parentNode = group.parentNode;

      for (var i = -1, n = group.length; ++i < n;) {
        if (node = group[i]) {
          subgroup.push(upgroup[i] = subnode = selector.call(group.parentNode, node.__data__, i));
          subnode.__data__ = node.__data__;
        } else {
          subgroup.push(null);
        }
      }
    }

    return d3_selection(subgroups);
  };

  d3_selectionPrototype.transition = function () {
    var id = d3_transitionInheritId || ++d3_transitionId,
        subgroups = [],
        subgroup,
        node,
        transition = Object.create(d3_transitionInherit);
    transition.time = Date.now();

    for (var j = -1, m = this.length; ++j < m;) {
      subgroups.push(subgroup = []);

      for (var group = this[j], i = -1, n = group.length; ++i < n;) {
        if (node = group[i]) d3_transitionNode(node, i, id, transition);
        subgroup.push(node);
      }
    }

    return d3_transition(subgroups, id);
  };

  var d3_selectionRoot = d3_selection([[d3_document]]);
  d3_selectionRoot[0].parentNode = d3_selectRoot;

  d3.select = function (selector) {
    return typeof selector === "string" ? d3_selectionRoot.select(selector) : d3_selection([[selector]]);
  };

  d3.selectAll = function (selector) {
    return typeof selector === "string" ? d3_selectionRoot.selectAll(selector) : d3_selection([d3_array(selector)]);
  };

  d3.behavior.zoom = function () {
    var translate = [0, 0],
        translate0,
        scale = 1,
        scale0,
        scaleExtent = d3_behavior_zoomInfinity,
        event = d3_eventDispatch(zoom, "zoom"),
        x0,
        x1,
        y0,
        y1,
        touchtime;

    function zoom() {
      this.on("mousedown.zoom", mousedown).on("mousemove.zoom", mousemove).on(d3_behavior_zoomWheel + ".zoom", mousewheel).on("dblclick.zoom", dblclick).on("touchstart.zoom", touchstart).on("touchmove.zoom", touchmove).on("touchend.zoom", touchstart);
    }

    zoom.translate = function (x) {
      if (!arguments.length) return translate;
      translate = x.map(Number);
      rescale();
      return zoom;
    };

    zoom.scale = function (x) {
      if (!arguments.length) return scale;
      scale = +x;
      rescale();
      return zoom;
    };

    zoom.scaleExtent = function (x) {
      if (!arguments.length) return scaleExtent;
      scaleExtent = x == null ? d3_behavior_zoomInfinity : x.map(Number);
      return zoom;
    };

    zoom.x = function (z) {
      if (!arguments.length) return x1;
      x1 = z;
      x0 = z.copy();
      translate = [0, 0];
      scale = 1;
      return zoom;
    };

    zoom.y = function (z) {
      if (!arguments.length) return y1;
      y1 = z;
      y0 = z.copy();
      translate = [0, 0];
      scale = 1;
      return zoom;
    };

    function location(p) {
      return [(p[0] - translate[0]) / scale, (p[1] - translate[1]) / scale];
    }

    function point(l) {
      return [l[0] * scale + translate[0], l[1] * scale + translate[1]];
    }

    function scaleTo(s) {
      scale = Math.max(scaleExtent[0], Math.min(scaleExtent[1], s));
    }

    function translateTo(p, l) {
      l = point(l);
      translate[0] += p[0] - l[0];
      translate[1] += p[1] - l[1];
    }

    function rescale() {
      if (x1) x1.domain(x0.range().map(function (x) {
        return (x - translate[0]) / scale;
      }).map(x0.invert));
      if (y1) y1.domain(y0.range().map(function (y) {
        return (y - translate[1]) / scale;
      }).map(y0.invert));
    }

    function dispatch(event) {
      rescale();
      d3.event.preventDefault();
      event({
        type: "zoom",
        scale: scale,
        translate: translate
      });
    }

    function mousedown() {
      var target = this,
          event_ = event.of(target, arguments),
          eventTarget = d3.event.target,
          moved = 0,
          w = d3.select(d3_window).on("mousemove.zoom", mousemove).on("mouseup.zoom", mouseup),
          l = location(d3.mouse(target));
      d3_window.focus();
      d3_eventCancel();

      function mousemove() {
        moved = 1;
        translateTo(d3.mouse(target), l);
        dispatch(event_);
      }

      function mouseup() {
        if (moved) d3_eventCancel();
        w.on("mousemove.zoom", null).on("mouseup.zoom", null);
        if (moved && d3.event.target === eventTarget) w.on("click.zoom", click, true);
      }

      function click() {
        d3_eventCancel();
        w.on("click.zoom", null);
      }
    }

    function mousewheel() {
      if (!translate0) translate0 = location(d3.mouse(this));
      scaleTo(Math.pow(2, d3_behavior_zoomDelta() * .002) * scale);
      translateTo(d3.mouse(this), translate0);
      dispatch(event.of(this, arguments));
    }

    function mousemove() {
      translate0 = null;
    }

    function dblclick() {
      var p = d3.mouse(this),
          l = location(p),
          k = Math.log(scale) / Math.LN2;
      scaleTo(Math.pow(2, d3.event.shiftKey ? Math.ceil(k) - 1 : Math.floor(k) + 1));
      translateTo(p, l);
      dispatch(event.of(this, arguments));
    }

    function touchstart() {
      var touches = d3.touches(this),
          now = Date.now();
      scale0 = scale;
      translate0 = {};
      touches.forEach(function (t) {
        translate0[t.identifier] = location(t);
      });
      d3_eventCancel();

      if (touches.length === 1) {
        if (now - touchtime < 500) {
          var p = touches[0],
              l = location(touches[0]);
          scaleTo(scale * 2);
          translateTo(p, l);
          dispatch(event.of(this, arguments));
        }

        touchtime = now;
      }
    }

    function touchmove() {
      var touches = d3.touches(this),
          p0 = touches[0],
          l0 = translate0[p0.identifier];

      if (p1 = touches[1]) {
        var p1,
            l1 = translate0[p1.identifier];
        p0 = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2];
        l0 = [(l0[0] + l1[0]) / 2, (l0[1] + l1[1]) / 2];
        scaleTo(d3.event.scale * scale0);
      }

      translateTo(p0, l0);
      touchtime = null;
      dispatch(event.of(this, arguments));
    }

    return d3.rebind(zoom, event, "on");
  };

  var d3_behavior_zoomInfinity = [0, Infinity];
  var d3_behavior_zoomDelta,
      d3_behavior_zoomWheel = "onwheel" in d3_document ? (d3_behavior_zoomDelta = function d3_behavior_zoomDelta() {
    return -d3.event.deltaY * (d3.event.deltaMode ? 120 : 1);
  }, "wheel") : "onmousewheel" in d3_document ? (d3_behavior_zoomDelta = function d3_behavior_zoomDelta() {
    return d3.event.wheelDelta;
  }, "mousewheel") : (d3_behavior_zoomDelta = function d3_behavior_zoomDelta() {
    return -d3.event.detail;
  }, "MozMousePixelScroll");

  function d3_Color() {}

  d3_Color.prototype.toString = function () {
    return this.rgb() + "";
  };

  d3.hsl = function (h, s, l) {
    return arguments.length === 1 ? h instanceof d3_Hsl ? d3_hsl(h.h, h.s, h.l) : d3_rgb_parse("" + h, d3_rgb_hsl, d3_hsl) : d3_hsl(+h, +s, +l);
  };

  function d3_hsl(h, s, l) {
    return new d3_Hsl(h, s, l);
  }

  function d3_Hsl(h, s, l) {
    this.h = h;
    this.s = s;
    this.l = l;
  }

  var d3_hslPrototype = d3_Hsl.prototype = new d3_Color();

  d3_hslPrototype.brighter = function (k) {
    k = Math.pow(.7, arguments.length ? k : 1);
    return d3_hsl(this.h, this.s, this.l / k);
  };

  d3_hslPrototype.darker = function (k) {
    k = Math.pow(.7, arguments.length ? k : 1);
    return d3_hsl(this.h, this.s, k * this.l);
  };

  d3_hslPrototype.rgb = function () {
    return d3_hsl_rgb(this.h, this.s, this.l);
  };

  function d3_hsl_rgb(h, s, l) {
    var m1, m2;
    h = h % 360;
    if (h < 0) h += 360;
    s = s < 0 ? 0 : s > 1 ? 1 : s;
    l = l < 0 ? 0 : l > 1 ? 1 : l;
    m2 = l <= .5 ? l * (1 + s) : l + s - l * s;
    m1 = 2 * l - m2;

    function v(h) {
      if (h > 360) h -= 360;else if (h < 0) h += 360;
      if (h < 60) return m1 + (m2 - m1) * h / 60;
      if (h < 180) return m2;
      if (h < 240) return m1 + (m2 - m1) * (240 - h) / 60;
      return m1;
    }

    function vv(h) {
      return Math.round(v(h) * 255);
    }

    return d3_rgb(vv(h + 120), vv(h), vv(h - 120));
  }

  var π = Math.PI,
      ε = 1e-6,
      d3_radians = π / 180,
      d3_degrees = 180 / π;

  function d3_sgn(x) {
    return x > 0 ? 1 : x < 0 ? -1 : 0;
  }

  function d3_acos(x) {
    return Math.acos(Math.max(-1, Math.min(1, x)));
  }

  function d3_asin(x) {
    return x > 1 ? π / 2 : x < -1 ? -π / 2 : Math.asin(x);
  }

  function d3_sinh(x) {
    return (Math.exp(x) - Math.exp(-x)) / 2;
  }

  function d3_cosh(x) {
    return (Math.exp(x) + Math.exp(-x)) / 2;
  }

  function d3_haversin(x) {
    return (x = Math.sin(x / 2)) * x;
  }

  d3.hcl = function (h, c, l) {
    return arguments.length === 1 ? h instanceof d3_Hcl ? d3_hcl(h.h, h.c, h.l) : h instanceof d3_Lab ? d3_lab_hcl(h.l, h.a, h.b) : d3_lab_hcl((h = d3_rgb_lab((h = d3.rgb(h)).r, h.g, h.b)).l, h.a, h.b) : d3_hcl(+h, +c, +l);
  };

  function d3_hcl(h, c, l) {
    return new d3_Hcl(h, c, l);
  }

  function d3_Hcl(h, c, l) {
    this.h = h;
    this.c = c;
    this.l = l;
  }

  var d3_hclPrototype = d3_Hcl.prototype = new d3_Color();

  d3_hclPrototype.brighter = function (k) {
    return d3_hcl(this.h, this.c, Math.min(100, this.l + d3_lab_K * (arguments.length ? k : 1)));
  };

  d3_hclPrototype.darker = function (k) {
    return d3_hcl(this.h, this.c, Math.max(0, this.l - d3_lab_K * (arguments.length ? k : 1)));
  };

  d3_hclPrototype.rgb = function () {
    return d3_hcl_lab(this.h, this.c, this.l).rgb();
  };

  function d3_hcl_lab(h, c, l) {
    return d3_lab(l, Math.cos(h *= d3_radians) * c, Math.sin(h) * c);
  }

  d3.lab = function (l, a, b) {
    return arguments.length === 1 ? l instanceof d3_Lab ? d3_lab(l.l, l.a, l.b) : l instanceof d3_Hcl ? d3_hcl_lab(l.l, l.c, l.h) : d3_rgb_lab((l = d3.rgb(l)).r, l.g, l.b) : d3_lab(+l, +a, +b);
  };

  function d3_lab(l, a, b) {
    return new d3_Lab(l, a, b);
  }

  function d3_Lab(l, a, b) {
    this.l = l;
    this.a = a;
    this.b = b;
  }

  var d3_lab_K = 18;
  var d3_lab_X = .95047,
      d3_lab_Y = 1,
      d3_lab_Z = 1.08883;
  var d3_labPrototype = d3_Lab.prototype = new d3_Color();

  d3_labPrototype.brighter = function (k) {
    return d3_lab(Math.min(100, this.l + d3_lab_K * (arguments.length ? k : 1)), this.a, this.b);
  };

  d3_labPrototype.darker = function (k) {
    return d3_lab(Math.max(0, this.l - d3_lab_K * (arguments.length ? k : 1)), this.a, this.b);
  };

  d3_labPrototype.rgb = function () {
    return d3_lab_rgb(this.l, this.a, this.b);
  };

  function d3_lab_rgb(l, a, b) {
    var y = (l + 16) / 116,
        x = y + a / 500,
        z = y - b / 200;
    x = d3_lab_xyz(x) * d3_lab_X;
    y = d3_lab_xyz(y) * d3_lab_Y;
    z = d3_lab_xyz(z) * d3_lab_Z;
    return d3_rgb(d3_xyz_rgb(3.2404542 * x - 1.5371385 * y - .4985314 * z), d3_xyz_rgb(-.969266 * x + 1.8760108 * y + .041556 * z), d3_xyz_rgb(.0556434 * x - .2040259 * y + 1.0572252 * z));
  }

  function d3_lab_hcl(l, a, b) {
    return d3_hcl(Math.atan2(b, a) * d3_degrees, Math.sqrt(a * a + b * b), l);
  }

  function d3_lab_xyz(x) {
    return x > .206893034 ? x * x * x : (x - 4 / 29) / 7.787037;
  }

  function d3_xyz_lab(x) {
    return x > .008856 ? Math.pow(x, 1 / 3) : 7.787037 * x + 4 / 29;
  }

  function d3_xyz_rgb(r) {
    return Math.round(255 * (r <= .00304 ? 12.92 * r : 1.055 * Math.pow(r, 1 / 2.4) - .055));
  }

  d3.rgb = function (r, g, b) {
    return arguments.length === 1 ? r instanceof d3_Rgb ? d3_rgb(r.r, r.g, r.b) : d3_rgb_parse("" + r, d3_rgb, d3_hsl_rgb) : d3_rgb(~~r, ~~g, ~~b);
  };

  function d3_rgb(r, g, b) {
    return new d3_Rgb(r, g, b);
  }

  function d3_Rgb(r, g, b) {
    this.r = r;
    this.g = g;
    this.b = b;
  }

  var d3_rgbPrototype = d3_Rgb.prototype = new d3_Color();

  d3_rgbPrototype.brighter = function (k) {
    k = Math.pow(.7, arguments.length ? k : 1);
    var r = this.r,
        g = this.g,
        b = this.b,
        i = 30;
    if (!r && !g && !b) return d3_rgb(i, i, i);
    if (r && r < i) r = i;
    if (g && g < i) g = i;
    if (b && b < i) b = i;
    return d3_rgb(Math.min(255, Math.floor(r / k)), Math.min(255, Math.floor(g / k)), Math.min(255, Math.floor(b / k)));
  };

  d3_rgbPrototype.darker = function (k) {
    k = Math.pow(.7, arguments.length ? k : 1);
    return d3_rgb(Math.floor(k * this.r), Math.floor(k * this.g), Math.floor(k * this.b));
  };

  d3_rgbPrototype.hsl = function () {
    return d3_rgb_hsl(this.r, this.g, this.b);
  };

  d3_rgbPrototype.toString = function () {
    return "#" + d3_rgb_hex(this.r) + d3_rgb_hex(this.g) + d3_rgb_hex(this.b);
  };

  function d3_rgb_hex(v) {
    return v < 16 ? "0" + Math.max(0, v).toString(16) : Math.min(255, v).toString(16);
  }

  function d3_rgb_parse(format, rgb, hsl) {
    var r = 0,
        g = 0,
        b = 0,
        m1,
        m2,
        name;
    m1 = /([a-z]+)\((.*)\)/i.exec(format);

    if (m1) {
      m2 = m1[2].split(",");

      switch (m1[1]) {
        case "hsl":
          {
            return hsl(parseFloat(m2[0]), parseFloat(m2[1]) / 100, parseFloat(m2[2]) / 100);
          }

        case "rgb":
          {
            return rgb(d3_rgb_parseNumber(m2[0]), d3_rgb_parseNumber(m2[1]), d3_rgb_parseNumber(m2[2]));
          }
      }
    }

    if (name = d3_rgb_names.get(format)) return rgb(name.r, name.g, name.b);

    if (format != null && format.charAt(0) === "#") {
      if (format.length === 4) {
        r = format.charAt(1);
        r += r;
        g = format.charAt(2);
        g += g;
        b = format.charAt(3);
        b += b;
      } else if (format.length === 7) {
        r = format.substring(1, 3);
        g = format.substring(3, 5);
        b = format.substring(5, 7);
      }

      r = parseInt(r, 16);
      g = parseInt(g, 16);
      b = parseInt(b, 16);
    }

    return rgb(r, g, b);
  }

  function d3_rgb_hsl(r, g, b) {
    var min = Math.min(r /= 255, g /= 255, b /= 255),
        max = Math.max(r, g, b),
        d = max - min,
        h,
        s,
        l = (max + min) / 2;

    if (d) {
      s = l < .5 ? d / (max + min) : d / (2 - max - min);
      if (r == max) h = (g - b) / d + (g < b ? 6 : 0);else if (g == max) h = (b - r) / d + 2;else h = (r - g) / d + 4;
      h *= 60;
    } else {
      s = h = 0;
    }

    return d3_hsl(h, s, l);
  }

  function d3_rgb_lab(r, g, b) {
    r = d3_rgb_xyz(r);
    g = d3_rgb_xyz(g);
    b = d3_rgb_xyz(b);
    var x = d3_xyz_lab((.4124564 * r + .3575761 * g + .1804375 * b) / d3_lab_X),
        y = d3_xyz_lab((.2126729 * r + .7151522 * g + .072175 * b) / d3_lab_Y),
        z = d3_xyz_lab((.0193339 * r + .119192 * g + .9503041 * b) / d3_lab_Z);
    return d3_lab(116 * y - 16, 500 * (x - y), 200 * (y - z));
  }

  function d3_rgb_xyz(r) {
    return (r /= 255) <= .04045 ? r / 12.92 : Math.pow((r + .055) / 1.055, 2.4);
  }

  function d3_rgb_parseNumber(c) {
    var f = parseFloat(c);
    return c.charAt(c.length - 1) === "%" ? Math.round(f * 2.55) : f;
  }

  var d3_rgb_names = d3.map({
    aliceblue: "#f0f8ff",
    antiquewhite: "#faebd7",
    aqua: "#00ffff",
    aquamarine: "#7fffd4",
    azure: "#f0ffff",
    beige: "#f5f5dc",
    bisque: "#ffe4c4",
    black: "#000000",
    blanchedalmond: "#ffebcd",
    blue: "#0000ff",
    blueviolet: "#8a2be2",
    brown: "#a52a2a",
    burlywood: "#deb887",
    cadetblue: "#5f9ea0",
    chartreuse: "#7fff00",
    chocolate: "#d2691e",
    coral: "#ff7f50",
    cornflowerblue: "#6495ed",
    cornsilk: "#fff8dc",
    crimson: "#dc143c",
    cyan: "#00ffff",
    darkblue: "#00008b",
    darkcyan: "#008b8b",
    darkgoldenrod: "#b8860b",
    darkgray: "#a9a9a9",
    darkgreen: "#006400",
    darkgrey: "#a9a9a9",
    darkkhaki: "#bdb76b",
    darkmagenta: "#8b008b",
    darkolivegreen: "#556b2f",
    darkorange: "#ff8c00",
    darkorchid: "#9932cc",
    darkred: "#8b0000",
    darksalmon: "#e9967a",
    darkseagreen: "#8fbc8f",
    darkslateblue: "#483d8b",
    darkslategray: "#2f4f4f",
    darkslategrey: "#2f4f4f",
    darkturquoise: "#00ced1",
    darkviolet: "#9400d3",
    deeppink: "#ff1493",
    deepskyblue: "#00bfff",
    dimgray: "#696969",
    dimgrey: "#696969",
    dodgerblue: "#1e90ff",
    firebrick: "#b22222",
    floralwhite: "#fffaf0",
    forestgreen: "#228b22",
    fuchsia: "#ff00ff",
    gainsboro: "#dcdcdc",
    ghostwhite: "#f8f8ff",
    gold: "#ffd700",
    goldenrod: "#daa520",
    gray: "#808080",
    green: "#008000",
    greenyellow: "#adff2f",
    grey: "#808080",
    honeydew: "#f0fff0",
    hotpink: "#ff69b4",
    indianred: "#cd5c5c",
    indigo: "#4b0082",
    ivory: "#fffff0",
    khaki: "#f0e68c",
    lavender: "#e6e6fa",
    lavenderblush: "#fff0f5",
    lawngreen: "#7cfc00",
    lemonchiffon: "#fffacd",
    lightblue: "#add8e6",
    lightcoral: "#f08080",
    lightcyan: "#e0ffff",
    lightgoldenrodyellow: "#fafad2",
    lightgray: "#d3d3d3",
    lightgreen: "#90ee90",
    lightgrey: "#d3d3d3",
    lightpink: "#ffb6c1",
    lightsalmon: "#ffa07a",
    lightseagreen: "#20b2aa",
    lightskyblue: "#87cefa",
    lightslategray: "#778899",
    lightslategrey: "#778899",
    lightsteelblue: "#b0c4de",
    lightyellow: "#ffffe0",
    lime: "#00ff00",
    limegreen: "#32cd32",
    linen: "#faf0e6",
    magenta: "#ff00ff",
    maroon: "#800000",
    mediumaquamarine: "#66cdaa",
    mediumblue: "#0000cd",
    mediumorchid: "#ba55d3",
    mediumpurple: "#9370db",
    mediumseagreen: "#3cb371",
    mediumslateblue: "#7b68ee",
    mediumspringgreen: "#00fa9a",
    mediumturquoise: "#48d1cc",
    mediumvioletred: "#c71585",
    midnightblue: "#191970",
    mintcream: "#f5fffa",
    mistyrose: "#ffe4e1",
    moccasin: "#ffe4b5",
    navajowhite: "#ffdead",
    navy: "#000080",
    oldlace: "#fdf5e6",
    olive: "#808000",
    olivedrab: "#6b8e23",
    orange: "#ffa500",
    orangered: "#ff4500",
    orchid: "#da70d6",
    palegoldenrod: "#eee8aa",
    palegreen: "#98fb98",
    paleturquoise: "#afeeee",
    palevioletred: "#db7093",
    papayawhip: "#ffefd5",
    peachpuff: "#ffdab9",
    peru: "#cd853f",
    pink: "#ffc0cb",
    plum: "#dda0dd",
    powderblue: "#b0e0e6",
    purple: "#800080",
    red: "#ff0000",
    rosybrown: "#bc8f8f",
    royalblue: "#4169e1",
    saddlebrown: "#8b4513",
    salmon: "#fa8072",
    sandybrown: "#f4a460",
    seagreen: "#2e8b57",
    seashell: "#fff5ee",
    sienna: "#a0522d",
    silver: "#c0c0c0",
    skyblue: "#87ceeb",
    slateblue: "#6a5acd",
    slategray: "#708090",
    slategrey: "#708090",
    snow: "#fffafa",
    springgreen: "#00ff7f",
    steelblue: "#4682b4",
    tan: "#d2b48c",
    teal: "#008080",
    thistle: "#d8bfd8",
    tomato: "#ff6347",
    turquoise: "#40e0d0",
    violet: "#ee82ee",
    wheat: "#f5deb3",
    white: "#ffffff",
    whitesmoke: "#f5f5f5",
    yellow: "#ffff00",
    yellowgreen: "#9acd32"
  });
  d3_rgb_names.forEach(function (key, value) {
    d3_rgb_names.set(key, d3_rgb_parse(value, d3_rgb, d3_hsl_rgb));
  });

  function d3_functor(v) {
    return typeof v === "function" ? v : function () {
      return v;
    };
  }

  d3.functor = d3_functor;

  function d3_identity(d) {
    return d;
  }

  d3.xhr = function (url, mimeType, callback) {
    var xhr = {},
        dispatch = d3.dispatch("progress", "load", "error"),
        headers = {},
        response = d3_identity,
        request = new (d3_window.XDomainRequest && /^(http(s)?:)?\/\//.test(url) ? XDomainRequest : XMLHttpRequest)();
    "onload" in request ? request.onload = request.onerror = respond : request.onreadystatechange = function () {
      request.readyState > 3 && respond();
    };

    function respond() {
      var s = request.status;
      !s && request.responseText || s >= 200 && s < 300 || s === 304 ? dispatch.load.call(xhr, response.call(xhr, request)) : dispatch.error.call(xhr, request);
    }

    request.onprogress = function (event) {
      var o = d3.event;
      d3.event = event;

      try {
        dispatch.progress.call(xhr, request);
      } finally {
        d3.event = o;
      }
    };

    xhr.header = function (name, value) {
      name = (name + "").toLowerCase();
      if (arguments.length < 2) return headers[name];
      if (value == null) delete headers[name];else headers[name] = value + "";
      return xhr;
    };

    xhr.mimeType = function (value) {
      if (!arguments.length) return mimeType;
      mimeType = value == null ? null : value + "";
      return xhr;
    };

    xhr.response = function (value) {
      response = value;
      return xhr;
    };

    ["get", "post"].forEach(function (method) {
      xhr[method] = function () {
        return xhr.send.apply(xhr, [method].concat(d3_array(arguments)));
      };
    });

    xhr.send = function (method, data, callback) {
      if (arguments.length === 2 && typeof data === "function") callback = data, data = null;
      request.open(method, url, true);
      if (mimeType != null && !("accept" in headers)) headers["accept"] = mimeType + ",*/*";
      if (request.setRequestHeader) for (var name in headers) {
        request.setRequestHeader(name, headers[name]);
      }
      if (mimeType != null && request.overrideMimeType) request.overrideMimeType(mimeType);
      if (callback != null) xhr.on("error", callback).on("load", function (request) {
        callback(null, request);
      });
      request.send(data == null ? null : data);
      return xhr;
    };

    xhr.abort = function () {
      request.abort();
      return xhr;
    };

    d3.rebind(xhr, dispatch, "on");
    if (arguments.length === 2 && typeof mimeType === "function") callback = mimeType, mimeType = null;
    return callback == null ? xhr : xhr.get(d3_xhr_fixCallback(callback));
  };

  function d3_xhr_fixCallback(callback) {
    return callback.length === 1 ? function (error, request) {
      callback(error == null ? request : null);
    } : callback;
  }

  function d3_dsv(delimiter, mimeType) {
    var reFormat = new RegExp('["' + delimiter + "\n]"),
        delimiterCode = delimiter.charCodeAt(0);

    function dsv(url, row, callback) {
      if (arguments.length < 3) callback = row, row = null;
      var xhr = d3.xhr(url, mimeType, callback);

      xhr.row = function (_) {
        return arguments.length ? xhr.response((row = _) == null ? response : typedResponse(_)) : row;
      };

      return xhr.row(row);
    }

    function response(request) {
      return dsv.parse(request.responseText);
    }

    function typedResponse(f) {
      return function (request) {
        return dsv.parse(request.responseText, f);
      };
    }

    dsv.parse = function (text, f) {
      var o;
      return dsv.parseRows(text, function (row, i) {
        if (o) return o(row, i - 1);
        var a = new Function("d", "return {" + row.map(function (name, i) {
          return JSON.stringify(name) + ": d[" + i + "]";
        }).join(",") + "}");
        o = f ? function (row, i) {
          return f(a(row), i);
        } : a;
      });
    };

    dsv.parseRows = function (text, f) {
      var EOL = {},
          EOF = {},
          rows = [],
          N = text.length,
          I = 0,
          n = 0,
          t,
          eol;

      function token() {
        if (I >= N) return EOF;
        if (eol) return eol = false, EOL;
        var j = I;

        if (text.charCodeAt(j) === 34) {
          var i = j;

          while (i++ < N) {
            if (text.charCodeAt(i) === 34) {
              if (text.charCodeAt(i + 1) !== 34) break;
              ++i;
            }
          }

          I = i + 2;
          var c = text.charCodeAt(i + 1);

          if (c === 13) {
            eol = true;
            if (text.charCodeAt(i + 2) === 10) ++I;
          } else if (c === 10) {
            eol = true;
          }

          return text.substring(j + 1, i).replace(/""/g, '"');
        }

        while (I < N) {
          var c = text.charCodeAt(I++),
              k = 1;
          if (c === 10) eol = true;else if (c === 13) {
            eol = true;
            if (text.charCodeAt(I) === 10) ++I, ++k;
          } else if (c !== delimiterCode) continue;
          return text.substring(j, I - k);
        }

        return text.substring(j);
      }

      while ((t = token()) !== EOF) {
        var a = [];

        while (t !== EOL && t !== EOF) {
          a.push(t);
          t = token();
        }

        if (f && !(a = f(a, n++))) continue;
        rows.push(a);
      }

      return rows;
    };

    dsv.format = function (rows) {
      if (Array.isArray(rows[0])) return dsv.formatRows(rows);
      var fieldSet = new d3_Set(),
          fields = [];
      rows.forEach(function (row) {
        for (var field in row) {
          if (!fieldSet.has(field)) {
            fields.push(fieldSet.add(field));
          }
        }
      });
      return [fields.map(formatValue).join(delimiter)].concat(rows.map(function (row) {
        return fields.map(function (field) {
          return formatValue(row[field]);
        }).join(delimiter);
      })).join("\n");
    };

    dsv.formatRows = function (rows) {
      return rows.map(formatRow).join("\n");
    };

    function formatRow(row) {
      return row.map(formatValue).join(delimiter);
    }

    function formatValue(text) {
      return reFormat.test(text) ? '"' + text.replace(/\"/g, '""') + '"' : text;
    }

    return dsv;
  }

  d3.csv = d3_dsv(",", "text/csv");
  d3.tsv = d3_dsv("	", "text/tab-separated-values");
  var d3_timer_id = 0,
      d3_timer_byId = {},
      d3_timer_queue = null,
      d3_timer_interval,
      d3_timer_timeout;

  d3.timer = function (callback, delay, then) {
    if (arguments.length < 3) {
      if (arguments.length < 2) delay = 0;else if (!isFinite(delay)) return;
      then = Date.now();
    }

    var timer = d3_timer_byId[callback.id];

    if (timer && timer.callback === callback) {
      timer.then = then;
      timer.delay = delay;
    } else d3_timer_byId[callback.id = ++d3_timer_id] = d3_timer_queue = {
      callback: callback,
      then: then,
      delay: delay,
      next: d3_timer_queue
    };

    if (!d3_timer_interval) {
      d3_timer_timeout = clearTimeout(d3_timer_timeout);
      d3_timer_interval = 1;
      d3_timer_frame(d3_timer_step);
    }
  };

  function d3_timer_step() {
    var elapsed,
        now = Date.now(),
        t1 = d3_timer_queue;

    while (t1) {
      elapsed = now - t1.then;
      if (elapsed >= t1.delay) t1.flush = t1.callback(elapsed);
      t1 = t1.next;
    }

    var delay = d3_timer_flush() - now;

    if (delay > 24) {
      if (isFinite(delay)) {
        clearTimeout(d3_timer_timeout);
        d3_timer_timeout = setTimeout(d3_timer_step, delay);
      }

      d3_timer_interval = 0;
    } else {
      d3_timer_interval = 1;
      d3_timer_frame(d3_timer_step);
    }
  }

  d3.timer.flush = function () {
    var elapsed,
        now = Date.now(),
        t1 = d3_timer_queue;

    while (t1) {
      elapsed = now - t1.then;
      if (!t1.delay) t1.flush = t1.callback(elapsed);
      t1 = t1.next;
    }

    d3_timer_flush();
  };

  function d3_timer_flush() {
    var t0 = null,
        t1 = d3_timer_queue,
        then = Infinity;

    while (t1) {
      if (t1.flush) {
        delete d3_timer_byId[t1.callback.id];
        t1 = t0 ? t0.next = t1.next : d3_timer_queue = t1.next;
      } else {
        then = Math.min(then, t1.then + t1.delay);
        t1 = (t0 = t1).next;
      }
    }

    return then;
  }

  var d3_timer_frame = d3_window.requestAnimationFrame || d3_window.webkitRequestAnimationFrame || d3_window.mozRequestAnimationFrame || d3_window.oRequestAnimationFrame || d3_window.msRequestAnimationFrame || function (callback) {
    setTimeout(callback, 17);
  };

  var d3_format_decimalPoint = ".",
      d3_format_thousandsSeparator = ",",
      d3_format_grouping = [3, 3];
  var d3_formatPrefixes = ["y", "z", "a", "f", "p", "n", "µ", "m", "", "k", "M", "G", "T", "P", "E", "Z", "Y"].map(d3_formatPrefix);

  d3.formatPrefix = function (value, precision) {
    var i = 0;

    if (value) {
      if (value < 0) value *= -1;
      if (precision) value = d3.round(value, d3_format_precision(value, precision));
      i = 1 + Math.floor(1e-12 + Math.log(value) / Math.LN10);
      i = Math.max(-24, Math.min(24, Math.floor((i <= 0 ? i + 1 : i - 1) / 3) * 3));
    }

    return d3_formatPrefixes[8 + i / 3];
  };

  function d3_formatPrefix(d, i) {
    var k = Math.pow(10, Math.abs(8 - i) * 3);
    return {
      scale: i > 8 ? function (d) {
        return d / k;
      } : function (d) {
        return d * k;
      },
      symbol: d
    };
  }

  d3.round = function (x, n) {
    return n ? Math.round(x * (n = Math.pow(10, n))) / n : Math.round(x);
  };

  d3.format = function (specifier) {
    var match = d3_format_re.exec(specifier),
        fill = match[1] || " ",
        align = match[2] || ">",
        sign = match[3] || "",
        basePrefix = match[4] || "",
        zfill = match[5],
        width = +match[6],
        comma = match[7],
        precision = match[8],
        type = match[9],
        scale = 1,
        suffix = "",
        integer = false;
    if (precision) precision = +precision.substring(1);

    if (zfill || fill === "0" && align === "=") {
      zfill = fill = "0";
      align = "=";
      if (comma) width -= Math.floor((width - 1) / 4);
    }

    switch (type) {
      case "n":
        comma = true;
        type = "g";
        break;

      case "%":
        scale = 100;
        suffix = "%";
        type = "f";
        break;

      case "p":
        scale = 100;
        suffix = "%";
        type = "r";
        break;

      case "b":
      case "o":
      case "x":
      case "X":
        if (basePrefix) basePrefix = "0" + type.toLowerCase();

      case "c":
      case "d":
        integer = true;
        precision = 0;
        break;

      case "s":
        scale = -1;
        type = "r";
        break;
    }

    if (basePrefix === "#") basePrefix = "";
    if (type == "r" && !precision) type = "g";

    if (precision != null) {
      if (type == "g") precision = Math.max(1, Math.min(21, precision));else if (type == "e" || type == "f") precision = Math.max(0, Math.min(20, precision));
    }

    type = d3_format_types.get(type) || d3_format_typeDefault;
    var zcomma = zfill && comma;
    return function (value) {
      if (integer && value % 1) return "";
      var negative = value < 0 || value === 0 && 1 / value < 0 ? (value = -value, "-") : sign;

      if (scale < 0) {
        var prefix = d3.formatPrefix(value, precision);
        value = prefix.scale(value);
        suffix = prefix.symbol;
      } else {
        value *= scale;
      }

      value = type(value, precision);
      if (!zfill && comma) value = d3_format_group(value);
      var length = basePrefix.length + value.length + (zcomma ? 0 : negative.length),
          padding = length < width ? new Array(length = width - length + 1).join(fill) : "";
      if (zcomma) value = d3_format_group(padding + value);
      if (d3_format_decimalPoint) value.replace(".", d3_format_decimalPoint);
      negative += basePrefix;
      return (align === "<" ? negative + value + padding : align === ">" ? padding + negative + value : align === "^" ? padding.substring(0, length >>= 1) + negative + value + padding.substring(length) : negative + (zcomma ? value : padding + value)) + suffix;
    };
  };

  var d3_format_re = /(?:([^{])?([<>=^]))?([+\- ])?(#)?(0)?(\d+)?(,)?(\.-?\d+)?([a-z%])?/i;
  var d3_format_types = d3.map({
    b: function b(x) {
      return x.toString(2);
    },
    c: function c(x) {
      return String.fromCharCode(x);
    },
    o: function o(x) {
      return x.toString(8);
    },
    x: function x(_x) {
      return _x.toString(16);
    },
    X: function X(x) {
      return x.toString(16).toUpperCase();
    },
    g: function g(x, p) {
      return x.toPrecision(p);
    },
    e: function e(x, p) {
      return x.toExponential(p);
    },
    f: function f(x, p) {
      return x.toFixed(p);
    },
    r: function r(x, p) {
      return (x = d3.round(x, d3_format_precision(x, p))).toFixed(Math.max(0, Math.min(20, d3_format_precision(x * (1 + 1e-15), p))));
    }
  });

  function d3_format_precision(x, p) {
    return p - (x ? Math.ceil(Math.log(x) / Math.LN10) : 1);
  }

  function d3_format_typeDefault(x) {
    return x + "";
  }

  var d3_format_group = d3_identity;

  if (d3_format_grouping) {
    var d3_format_groupingLength = d3_format_grouping.length;

    d3_format_group = function d3_format_group(value) {
      var i = value.lastIndexOf("."),
          f = i >= 0 ? "." + value.substring(i + 1) : (i = value.length, ""),
          t = [],
          j = 0,
          g = d3_format_grouping[0];

      while (i > 0 && g > 0) {
        t.push(value.substring(i -= g, i + g));
        g = d3_format_grouping[j = (j + 1) % d3_format_groupingLength];
      }

      return t.reverse().join(d3_format_thousandsSeparator || "") + f;
    };
  }

  d3.geo = {};

  d3.geo.stream = function (object, listener) {
    if (d3_geo_streamObjectType.hasOwnProperty(object.type)) {
      d3_geo_streamObjectType[object.type](object, listener);
    } else {
      d3_geo_streamGeometry(object, listener);
    }
  };

  function d3_geo_streamGeometry(geometry, listener) {
    if (d3_geo_streamGeometryType.hasOwnProperty(geometry.type)) {
      d3_geo_streamGeometryType[geometry.type](geometry, listener);
    }
  }

  var d3_geo_streamObjectType = {
    Feature: function Feature(feature, listener) {
      d3_geo_streamGeometry(feature.geometry, listener);
    },
    FeatureCollection: function FeatureCollection(object, listener) {
      var features = object.features,
          i = -1,
          n = features.length;

      while (++i < n) {
        d3_geo_streamGeometry(features[i].geometry, listener);
      }
    }
  };
  var d3_geo_streamGeometryType = {
    Sphere: function Sphere(object, listener) {
      listener.sphere();
    },
    Point: function Point(object, listener) {
      var coordinate = object.coordinates;
      listener.point(coordinate[0], coordinate[1]);
    },
    MultiPoint: function MultiPoint(object, listener) {
      var coordinates = object.coordinates,
          i = -1,
          n = coordinates.length,
          coordinate;

      while (++i < n) {
        coordinate = coordinates[i], listener.point(coordinate[0], coordinate[1]);
      }
    },
    LineString: function LineString(object, listener) {
      d3_geo_streamLine(object.coordinates, listener, 0);
    },
    MultiLineString: function MultiLineString(object, listener) {
      var coordinates = object.coordinates,
          i = -1,
          n = coordinates.length;

      while (++i < n) {
        d3_geo_streamLine(coordinates[i], listener, 0);
      }
    },
    Polygon: function Polygon(object, listener) {
      d3_geo_streamPolygon(object.coordinates, listener);
    },
    MultiPolygon: function MultiPolygon(object, listener) {
      var coordinates = object.coordinates,
          i = -1,
          n = coordinates.length;

      while (++i < n) {
        d3_geo_streamPolygon(coordinates[i], listener);
      }
    },
    GeometryCollection: function GeometryCollection(object, listener) {
      var geometries = object.geometries,
          i = -1,
          n = geometries.length;

      while (++i < n) {
        d3_geo_streamGeometry(geometries[i], listener);
      }
    }
  };

  function d3_geo_streamLine(coordinates, listener, closed) {
    var i = -1,
        n = coordinates.length - closed,
        coordinate;
    listener.lineStart();

    while (++i < n) {
      coordinate = coordinates[i], listener.point(coordinate[0], coordinate[1]);
    }

    listener.lineEnd();
  }

  function d3_geo_streamPolygon(coordinates, listener) {
    var i = -1,
        n = coordinates.length;
    listener.polygonStart();

    while (++i < n) {
      d3_geo_streamLine(coordinates[i], listener, 1);
    }

    listener.polygonEnd();
  }

  d3.geo.area = function (object) {
    d3_geo_areaSum = 0;
    d3.geo.stream(object, d3_geo_area);
    return d3_geo_areaSum;
  };

  var d3_geo_areaSum, d3_geo_areaRingU, d3_geo_areaRingV;
  var d3_geo_area = {
    sphere: function sphere() {
      d3_geo_areaSum += 4 * π;
    },
    point: d3_noop,
    lineStart: d3_noop,
    lineEnd: d3_noop,
    polygonStart: function polygonStart() {
      d3_geo_areaRingU = 1, d3_geo_areaRingV = 0;
      d3_geo_area.lineStart = d3_geo_areaRingStart;
    },
    polygonEnd: function polygonEnd() {
      var area = 2 * Math.atan2(d3_geo_areaRingV, d3_geo_areaRingU);
      d3_geo_areaSum += area < 0 ? 4 * π + area : area;
      d3_geo_area.lineStart = d3_geo_area.lineEnd = d3_geo_area.point = d3_noop;
    }
  };

  function d3_geo_areaRingStart() {
    var λ00, φ00, λ0, cosφ0, sinφ0;

    d3_geo_area.point = function (λ, φ) {
      d3_geo_area.point = nextPoint;
      λ0 = (λ00 = λ) * d3_radians, cosφ0 = Math.cos(φ = (φ00 = φ) * d3_radians / 2 + π / 4), sinφ0 = Math.sin(φ);
    };

    function nextPoint(λ, φ) {
      λ *= d3_radians;
      φ = φ * d3_radians / 2 + π / 4;
      var dλ = λ - λ0,
          cosφ = Math.cos(φ),
          sinφ = Math.sin(φ),
          k = sinφ0 * sinφ,
          u0 = d3_geo_areaRingU,
          v0 = d3_geo_areaRingV,
          u = cosφ0 * cosφ + k * Math.cos(dλ),
          v = k * Math.sin(dλ);
      d3_geo_areaRingU = u0 * u - v0 * v;
      d3_geo_areaRingV = v0 * u + u0 * v;
      λ0 = λ, cosφ0 = cosφ, sinφ0 = sinφ;
    }

    d3_geo_area.lineEnd = function () {
      nextPoint(λ00, φ00);
    };
  }

  d3.geo.bounds = d3_geo_bounds(d3_identity);

  function d3_geo_bounds(projectStream) {
    var x0, y0, x1, y1;
    var bound = {
      point: boundPoint,
      lineStart: d3_noop,
      lineEnd: d3_noop,
      polygonStart: function polygonStart() {
        bound.lineEnd = boundPolygonLineEnd;
      },
      polygonEnd: function polygonEnd() {
        bound.point = boundPoint;
      }
    };

    function boundPoint(x, y) {
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }

    function boundPolygonLineEnd() {
      bound.point = bound.lineEnd = d3_noop;
    }

    return function (feature) {
      y1 = x1 = -(x0 = y0 = Infinity);
      d3.geo.stream(feature, projectStream(bound));
      return [[x0, y0], [x1, y1]];
    };
  }

  d3.geo.centroid = function (object) {
    d3_geo_centroidDimension = d3_geo_centroidW = d3_geo_centroidX = d3_geo_centroidY = d3_geo_centroidZ = 0;
    d3.geo.stream(object, d3_geo_centroid);
    var m;

    if (d3_geo_centroidW && Math.abs(m = Math.sqrt(d3_geo_centroidX * d3_geo_centroidX + d3_geo_centroidY * d3_geo_centroidY + d3_geo_centroidZ * d3_geo_centroidZ)) > ε) {
      return [Math.atan2(d3_geo_centroidY, d3_geo_centroidX) * d3_degrees, Math.asin(Math.max(-1, Math.min(1, d3_geo_centroidZ / m))) * d3_degrees];
    }
  };

  var d3_geo_centroidDimension, d3_geo_centroidW, d3_geo_centroidX, d3_geo_centroidY, d3_geo_centroidZ;
  var d3_geo_centroid = {
    sphere: function sphere() {
      if (d3_geo_centroidDimension < 2) {
        d3_geo_centroidDimension = 2;
        d3_geo_centroidW = d3_geo_centroidX = d3_geo_centroidY = d3_geo_centroidZ = 0;
      }
    },
    point: d3_geo_centroidPoint,
    lineStart: d3_geo_centroidLineStart,
    lineEnd: d3_geo_centroidLineEnd,
    polygonStart: function polygonStart() {
      if (d3_geo_centroidDimension < 2) {
        d3_geo_centroidDimension = 2;
        d3_geo_centroidW = d3_geo_centroidX = d3_geo_centroidY = d3_geo_centroidZ = 0;
      }

      d3_geo_centroid.lineStart = d3_geo_centroidRingStart;
    },
    polygonEnd: function polygonEnd() {
      d3_geo_centroid.lineStart = d3_geo_centroidLineStart;
    }
  };

  function d3_geo_centroidPoint(λ, φ) {
    if (d3_geo_centroidDimension) return;
    ++d3_geo_centroidW;
    λ *= d3_radians;
    var cosφ = Math.cos(φ *= d3_radians);
    d3_geo_centroidX += (cosφ * Math.cos(λ) - d3_geo_centroidX) / d3_geo_centroidW;
    d3_geo_centroidY += (cosφ * Math.sin(λ) - d3_geo_centroidY) / d3_geo_centroidW;
    d3_geo_centroidZ += (Math.sin(φ) - d3_geo_centroidZ) / d3_geo_centroidW;
  }

  function d3_geo_centroidRingStart() {
    var λ00, φ00;
    d3_geo_centroidDimension = 1;
    d3_geo_centroidLineStart();
    d3_geo_centroidDimension = 2;
    var linePoint = d3_geo_centroid.point;

    d3_geo_centroid.point = function (λ, φ) {
      linePoint(λ00 = λ, φ00 = φ);
    };

    d3_geo_centroid.lineEnd = function () {
      d3_geo_centroid.point(λ00, φ00);
      d3_geo_centroidLineEnd();
      d3_geo_centroid.lineEnd = d3_geo_centroidLineEnd;
    };
  }

  function d3_geo_centroidLineStart() {
    var x0, y0, z0;
    if (d3_geo_centroidDimension > 1) return;

    if (d3_geo_centroidDimension < 1) {
      d3_geo_centroidDimension = 1;
      d3_geo_centroidW = d3_geo_centroidX = d3_geo_centroidY = d3_geo_centroidZ = 0;
    }

    d3_geo_centroid.point = function (λ, φ) {
      λ *= d3_radians;
      var cosφ = Math.cos(φ *= d3_radians);
      x0 = cosφ * Math.cos(λ);
      y0 = cosφ * Math.sin(λ);
      z0 = Math.sin(φ);
      d3_geo_centroid.point = nextPoint;
    };

    function nextPoint(λ, φ) {
      λ *= d3_radians;
      var cosφ = Math.cos(φ *= d3_radians),
          x = cosφ * Math.cos(λ),
          y = cosφ * Math.sin(λ),
          z = Math.sin(φ),
          w = Math.atan2(Math.sqrt((w = y0 * z - z0 * y) * w + (w = z0 * x - x0 * z) * w + (w = x0 * y - y0 * x) * w), x0 * x + y0 * y + z0 * z);
      d3_geo_centroidW += w;
      d3_geo_centroidX += w * (x0 + (x0 = x));
      d3_geo_centroidY += w * (y0 + (y0 = y));
      d3_geo_centroidZ += w * (z0 + (z0 = z));
    }
  }

  function d3_geo_centroidLineEnd() {
    d3_geo_centroid.point = d3_geo_centroidPoint;
  }

  function d3_geo_cartesian(spherical) {
    var λ = spherical[0],
        φ = spherical[1],
        cosφ = Math.cos(φ);
    return [cosφ * Math.cos(λ), cosφ * Math.sin(λ), Math.sin(φ)];
  }

  function d3_geo_cartesianDot(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  }

  function d3_geo_cartesianCross(a, b) {
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  }

  function d3_geo_cartesianAdd(a, b) {
    a[0] += b[0];
    a[1] += b[1];
    a[2] += b[2];
  }

  function d3_geo_cartesianScale(vector, k) {
    return [vector[0] * k, vector[1] * k, vector[2] * k];
  }

  function d3_geo_cartesianNormalize(d) {
    var l = Math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    d[0] /= l;
    d[1] /= l;
    d[2] /= l;
  }

  function d3_true() {
    return true;
  }

  function d3_geo_spherical(cartesian) {
    return [Math.atan2(cartesian[1], cartesian[0]), Math.asin(Math.max(-1, Math.min(1, cartesian[2])))];
  }

  function d3_geo_sphericalEqual(a, b) {
    return Math.abs(a[0] - b[0]) < ε && Math.abs(a[1] - b[1]) < ε;
  }

  function d3_geo_clipPolygon(segments, compare, inside, interpolate, listener) {
    var subject = [],
        clip = [];
    segments.forEach(function (segment) {
      if ((n = segment.length - 1) <= 0) return;
      var n,
          p0 = segment[0],
          p1 = segment[n];

      if (d3_geo_sphericalEqual(p0, p1)) {
        listener.lineStart();

        for (var i = 0; i < n; ++i) {
          listener.point((p0 = segment[i])[0], p0[1]);
        }

        listener.lineEnd();
        return;
      }

      var a = {
        point: p0,
        points: segment,
        other: null,
        visited: false,
        entry: true,
        subject: true
      },
          b = {
        point: p0,
        points: [p0],
        other: a,
        visited: false,
        entry: false,
        subject: false
      };
      a.other = b;
      subject.push(a);
      clip.push(b);
      a = {
        point: p1,
        points: [p1],
        other: null,
        visited: false,
        entry: false,
        subject: true
      };
      b = {
        point: p1,
        points: [p1],
        other: a,
        visited: false,
        entry: true,
        subject: false
      };
      a.other = b;
      subject.push(a);
      clip.push(b);
    });
    clip.sort(compare);
    d3_geo_clipPolygonLinkCircular(subject);
    d3_geo_clipPolygonLinkCircular(clip);
    if (!subject.length) return;
    if (inside) for (var i = 1, e = !inside(clip[0].point), n = clip.length; i < n; ++i) {
      clip[i].entry = e = !e;
    }
    var start = subject[0],
        current,
        points,
        point;

    while (1) {
      current = start;

      while (current.visited) {
        if ((current = current.next) === start) return;
      }

      points = current.points;
      listener.lineStart();

      do {
        current.visited = current.other.visited = true;

        if (current.entry) {
          if (current.subject) {
            for (var i = 0; i < points.length; i++) {
              listener.point((point = points[i])[0], point[1]);
            }
          } else {
            interpolate(current.point, current.next.point, 1, listener);
          }

          current = current.next;
        } else {
          if (current.subject) {
            points = current.prev.points;

            for (var i = points.length; --i >= 0;) {
              listener.point((point = points[i])[0], point[1]);
            }
          } else {
            interpolate(current.point, current.prev.point, -1, listener);
          }

          current = current.prev;
        }

        current = current.other;
        points = current.points;
      } while (!current.visited);

      listener.lineEnd();
    }
  }

  function d3_geo_clipPolygonLinkCircular(array) {
    if (!(n = array.length)) return;
    var n,
        i = 0,
        a = array[0],
        b;

    while (++i < n) {
      a.next = b = array[i];
      b.prev = a;
      a = b;
    }

    a.next = b = array[0];
    b.prev = a;
  }

  function d3_geo_clip(pointVisible, clipLine, interpolate) {
    return function (listener) {
      var line = clipLine(listener);
      var clip = {
        point: point,
        lineStart: lineStart,
        lineEnd: lineEnd,
        polygonStart: function polygonStart() {
          clip.point = pointRing;
          clip.lineStart = ringStart;
          clip.lineEnd = ringEnd;
          invisible = false;
          invisibleArea = visibleArea = 0;
          segments = [];
          listener.polygonStart();
        },
        polygonEnd: function polygonEnd() {
          clip.point = point;
          clip.lineStart = lineStart;
          clip.lineEnd = lineEnd;
          segments = d3.merge(segments);

          if (segments.length) {
            d3_geo_clipPolygon(segments, d3_geo_clipSort, null, interpolate, listener);
          } else if (visibleArea < -ε || invisible && invisibleArea < -ε) {
            listener.lineStart();
            interpolate(null, null, 1, listener);
            listener.lineEnd();
          }

          listener.polygonEnd();
          segments = null;
        },
        sphere: function sphere() {
          listener.polygonStart();
          listener.lineStart();
          interpolate(null, null, 1, listener);
          listener.lineEnd();
          listener.polygonEnd();
        }
      };

      function point(λ, φ) {
        if (pointVisible(λ, φ)) listener.point(λ, φ);
      }

      function pointLine(λ, φ) {
        line.point(λ, φ);
      }

      function lineStart() {
        clip.point = pointLine;
        line.lineStart();
      }

      function lineEnd() {
        clip.point = point;
        line.lineEnd();
      }

      var segments, visibleArea, invisibleArea, invisible;
      var buffer = d3_geo_clipBufferListener(),
          ringListener = clipLine(buffer),
          ring;

      function pointRing(λ, φ) {
        ringListener.point(λ, φ);
        ring.push([λ, φ]);
      }

      function ringStart() {
        ringListener.lineStart();
        ring = [];
      }

      function ringEnd() {
        pointRing(ring[0][0], ring[0][1]);
        ringListener.lineEnd();
        var clean = ringListener.clean(),
            ringSegments = buffer.buffer(),
            segment,
            n = ringSegments.length;

        if (!n) {
          invisible = true;
          invisibleArea += d3_geo_clipAreaRing(ring, -1);
          ring = null;
          return;
        }

        ring = null;

        if (clean & 1) {
          segment = ringSegments[0];
          visibleArea += d3_geo_clipAreaRing(segment, 1);
          var n = segment.length - 1,
              i = -1,
              point;
          listener.lineStart();

          while (++i < n) {
            listener.point((point = segment[i])[0], point[1]);
          }

          listener.lineEnd();
          return;
        }

        if (n > 1 && clean & 2) ringSegments.push(ringSegments.pop().concat(ringSegments.shift()));
        segments.push(ringSegments.filter(d3_geo_clipSegmentLength1));
      }

      return clip;
    };
  }

  function d3_geo_clipSegmentLength1(segment) {
    return segment.length > 1;
  }

  function d3_geo_clipBufferListener() {
    var lines = [],
        line;
    return {
      lineStart: function lineStart() {
        lines.push(line = []);
      },
      point: function point(λ, φ) {
        line.push([λ, φ]);
      },
      lineEnd: d3_noop,
      buffer: function buffer() {
        var buffer = lines;
        lines = [];
        line = null;
        return buffer;
      },
      rejoin: function rejoin() {
        if (lines.length > 1) lines.push(lines.pop().concat(lines.shift()));
      }
    };
  }

  function d3_geo_clipAreaRing(ring, invisible) {
    if (!(n = ring.length)) return 0;
    var n,
        i = 0,
        area = 0,
        p = ring[0],
        λ = p[0],
        φ = p[1],
        cosφ = Math.cos(φ),
        x0 = Math.atan2(invisible * Math.sin(λ) * cosφ, Math.sin(φ)),
        y0 = 1 - invisible * Math.cos(λ) * cosφ,
        x1 = x0,
        x,
        y;

    while (++i < n) {
      p = ring[i];
      cosφ = Math.cos(φ = p[1]);
      x = Math.atan2(invisible * Math.sin(λ = p[0]) * cosφ, Math.sin(φ));
      y = 1 - invisible * Math.cos(λ) * cosφ;
      if (Math.abs(y0 - 2) < ε && Math.abs(y - 2) < ε) continue;

      if (Math.abs(y) < ε || Math.abs(y0) < ε) {} else if (Math.abs(Math.abs(x - x0) - π) < ε) {
        if (y + y0 > 2) area += 4 * (x - x0);
      } else if (Math.abs(y0 - 2) < ε) area += 4 * (x - x1);else area += ((3 * π + x - x0) % (2 * π) - π) * (y0 + y);

      x1 = x0, x0 = x, y0 = y;
    }

    return area;
  }

  function d3_geo_clipSort(a, b) {
    return ((a = a.point)[0] < 0 ? a[1] - π / 2 - ε : π / 2 - a[1]) - ((b = b.point)[0] < 0 ? b[1] - π / 2 - ε : π / 2 - b[1]);
  }

  var d3_geo_clipAntimeridian = d3_geo_clip(d3_true, d3_geo_clipAntimeridianLine, d3_geo_clipAntimeridianInterpolate);

  function d3_geo_clipAntimeridianLine(listener) {
    var λ0 = NaN,
        φ0 = NaN,
        sλ0 = NaN,
        _clean;

    return {
      lineStart: function lineStart() {
        listener.lineStart();
        _clean = 1;
      },
      point: function point(λ1, φ1) {
        var sλ1 = λ1 > 0 ? π : -π,
            dλ = Math.abs(λ1 - λ0);

        if (Math.abs(dλ - π) < ε) {
          listener.point(λ0, φ0 = (φ0 + φ1) / 2 > 0 ? π / 2 : -π / 2);
          listener.point(sλ0, φ0);
          listener.lineEnd();
          listener.lineStart();
          listener.point(sλ1, φ0);
          listener.point(λ1, φ0);
          _clean = 0;
        } else if (sλ0 !== sλ1 && dλ >= π) {
          if (Math.abs(λ0 - sλ0) < ε) λ0 -= sλ0 * ε;
          if (Math.abs(λ1 - sλ1) < ε) λ1 -= sλ1 * ε;
          φ0 = d3_geo_clipAntimeridianIntersect(λ0, φ0, λ1, φ1);
          listener.point(sλ0, φ0);
          listener.lineEnd();
          listener.lineStart();
          listener.point(sλ1, φ0);
          _clean = 0;
        }

        listener.point(λ0 = λ1, φ0 = φ1);
        sλ0 = sλ1;
      },
      lineEnd: function lineEnd() {
        listener.lineEnd();
        λ0 = φ0 = NaN;
      },
      clean: function clean() {
        return 2 - _clean;
      }
    };
  }

  function d3_geo_clipAntimeridianIntersect(λ0, φ0, λ1, φ1) {
    var cosφ0,
        cosφ1,
        sinλ0_λ1 = Math.sin(λ0 - λ1);
    return Math.abs(sinλ0_λ1) > ε ? Math.atan((Math.sin(φ0) * (cosφ1 = Math.cos(φ1)) * Math.sin(λ1) - Math.sin(φ1) * (cosφ0 = Math.cos(φ0)) * Math.sin(λ0)) / (cosφ0 * cosφ1 * sinλ0_λ1)) : (φ0 + φ1) / 2;
  }

  function d3_geo_clipAntimeridianInterpolate(from, to, direction, listener) {
    var φ;

    if (from == null) {
      φ = direction * π / 2;
      listener.point(-π, φ);
      listener.point(0, φ);
      listener.point(π, φ);
      listener.point(π, 0);
      listener.point(π, -φ);
      listener.point(0, -φ);
      listener.point(-π, -φ);
      listener.point(-π, 0);
      listener.point(-π, φ);
    } else if (Math.abs(from[0] - to[0]) > ε) {
      var s = (from[0] < to[0] ? 1 : -1) * π;
      φ = direction * s / 2;
      listener.point(-s, φ);
      listener.point(0, φ);
      listener.point(s, φ);
    } else {
      listener.point(to[0], to[1]);
    }
  }

  function d3_geo_clipCircle(radius) {
    var cr = Math.cos(radius),
        smallRadius = cr > 0,
        notHemisphere = Math.abs(cr) > ε,
        interpolate = d3_geo_circleInterpolate(radius, 6 * d3_radians);
    return d3_geo_clip(visible, clipLine, interpolate);

    function visible(λ, φ) {
      return Math.cos(λ) * Math.cos(φ) > cr;
    }

    function clipLine(listener) {
      var point0, c0, v0, v00, _clean2;

      return {
        lineStart: function lineStart() {
          v00 = v0 = false;
          _clean2 = 1;
        },
        point: function point(λ, φ) {
          var point1 = [λ, φ],
              point2,
              v = visible(λ, φ),
              c = smallRadius ? v ? 0 : code(λ, φ) : v ? code(λ + (λ < 0 ? π : -π), φ) : 0;
          if (!point0 && (v00 = v0 = v)) listener.lineStart();

          if (v !== v0) {
            point2 = intersect(point0, point1);

            if (d3_geo_sphericalEqual(point0, point2) || d3_geo_sphericalEqual(point1, point2)) {
              point1[0] += ε;
              point1[1] += ε;
              v = visible(point1[0], point1[1]);
            }
          }

          if (v !== v0) {
            _clean2 = 0;

            if (v) {
              listener.lineStart();
              point2 = intersect(point1, point0);
              listener.point(point2[0], point2[1]);
            } else {
              point2 = intersect(point0, point1);
              listener.point(point2[0], point2[1]);
              listener.lineEnd();
            }

            point0 = point2;
          } else if (notHemisphere && point0 && smallRadius ^ v) {
            var t;

            if (!(c & c0) && (t = intersect(point1, point0, true))) {
              _clean2 = 0;

              if (smallRadius) {
                listener.lineStart();
                listener.point(t[0][0], t[0][1]);
                listener.point(t[1][0], t[1][1]);
                listener.lineEnd();
              } else {
                listener.point(t[1][0], t[1][1]);
                listener.lineEnd();
                listener.lineStart();
                listener.point(t[0][0], t[0][1]);
              }
            }
          }

          if (v && (!point0 || !d3_geo_sphericalEqual(point0, point1))) {
            listener.point(point1[0], point1[1]);
          }

          point0 = point1, v0 = v, c0 = c;
        },
        lineEnd: function lineEnd() {
          if (v0) listener.lineEnd();
          point0 = null;
        },
        clean: function clean() {
          return _clean2 | (v00 && v0) << 1;
        }
      };
    }

    function intersect(a, b, two) {
      var pa = d3_geo_cartesian(a),
          pb = d3_geo_cartesian(b);
      var n1 = [1, 0, 0],
          n2 = d3_geo_cartesianCross(pa, pb),
          n2n2 = d3_geo_cartesianDot(n2, n2),
          n1n2 = n2[0],
          determinant = n2n2 - n1n2 * n1n2;
      if (!determinant) return !two && a;
      var c1 = cr * n2n2 / determinant,
          c2 = -cr * n1n2 / determinant,
          n1xn2 = d3_geo_cartesianCross(n1, n2),
          A = d3_geo_cartesianScale(n1, c1),
          B = d3_geo_cartesianScale(n2, c2);
      d3_geo_cartesianAdd(A, B);
      var u = n1xn2,
          w = d3_geo_cartesianDot(A, u),
          uu = d3_geo_cartesianDot(u, u),
          t2 = w * w - uu * (d3_geo_cartesianDot(A, A) - 1);
      if (t2 < 0) return;
      var t = Math.sqrt(t2),
          q = d3_geo_cartesianScale(u, (-w - t) / uu);
      d3_geo_cartesianAdd(q, A);
      q = d3_geo_spherical(q);
      if (!two) return q;
      var λ0 = a[0],
          λ1 = b[0],
          φ0 = a[1],
          φ1 = b[1],
          z;
      if (λ1 < λ0) z = λ0, λ0 = λ1, λ1 = z;
      var δλ = λ1 - λ0,
          polar = Math.abs(δλ - π) < ε,
          meridian = polar || δλ < ε;
      if (!polar && φ1 < φ0) z = φ0, φ0 = φ1, φ1 = z;

      if (meridian ? polar ? φ0 + φ1 > 0 ^ q[1] < (Math.abs(q[0] - λ0) < ε ? φ0 : φ1) : φ0 <= q[1] && q[1] <= φ1 : δλ > π ^ (λ0 <= q[0] && q[0] <= λ1)) {
        var q1 = d3_geo_cartesianScale(u, (-w + t) / uu);
        d3_geo_cartesianAdd(q1, A);
        return [q, d3_geo_spherical(q1)];
      }
    }

    function code(λ, φ) {
      var r = smallRadius ? radius : π - radius,
          code = 0;
      if (λ < -r) code |= 1;else if (λ > r) code |= 2;
      if (φ < -r) code |= 4;else if (φ > r) code |= 8;
      return code;
    }
  }

  var d3_geo_clipViewMAX = 1e9;

  function d3_geo_clipView(x0, y0, x1, y1) {
    return function (listener) {
      var listener_ = listener,
          bufferListener = d3_geo_clipBufferListener(),
          segments,
          polygon,
          ring;
      var clip = {
        point: point,
        lineStart: lineStart,
        lineEnd: lineEnd,
        polygonStart: function polygonStart() {
          listener = bufferListener;
          segments = [];
          polygon = [];
        },
        polygonEnd: function polygonEnd() {
          listener = listener_;

          if ((segments = d3.merge(segments)).length) {
            listener.polygonStart();
            d3_geo_clipPolygon(segments, compare, inside, interpolate, listener);
            listener.polygonEnd();
          } else if (insidePolygon([x0, y0])) {
            listener.polygonStart(), listener.lineStart();
            interpolate(null, null, 1, listener);
            listener.lineEnd(), listener.polygonEnd();
          }

          segments = polygon = ring = null;
        }
      };

      function inside(point) {
        var a = corner(point, -1),
            i = insidePolygon([a === 0 || a === 3 ? x0 : x1, a > 1 ? y1 : y0]);
        return i;
      }

      function insidePolygon(p) {
        var wn = 0,
            n = polygon.length,
            y = p[1];

        for (var i = 0; i < n; ++i) {
          for (var j = 1, v = polygon[i], m = v.length, a = v[0]; j < m; ++j) {
            b = v[j];

            if (a[1] <= y) {
              if (b[1] > y && isLeft(a, b, p) > 0) ++wn;
            } else {
              if (b[1] <= y && isLeft(a, b, p) < 0) --wn;
            }

            a = b;
          }
        }

        return wn !== 0;
      }

      function isLeft(a, b, c) {
        return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]);
      }

      function interpolate(from, to, direction, listener) {
        var a = 0,
            a1 = 0;

        if (from == null || (a = corner(from, direction)) !== (a1 = corner(to, direction)) || comparePoints(from, to) < 0 ^ direction > 0) {
          do {
            listener.point(a === 0 || a === 3 ? x0 : x1, a > 1 ? y1 : y0);
          } while ((a = (a + direction + 4) % 4) !== a1);
        } else {
          listener.point(to[0], to[1]);
        }
      }

      function visible(x, y) {
        return x0 <= x && x <= x1 && y0 <= y && y <= y1;
      }

      function point(x, y) {
        if (visible(x, y)) listener.point(x, y);
      }

      var x__, y__, v__, x_, y_, v_, first;

      function lineStart() {
        clip.point = linePoint;
        if (polygon) polygon.push(ring = []);
        first = true;
        v_ = false;
        x_ = y_ = NaN;
      }

      function lineEnd() {
        if (segments) {
          linePoint(x__, y__);
          if (v__ && v_) bufferListener.rejoin();
          segments.push(bufferListener.buffer());
        }

        clip.point = point;
        if (v_) listener.lineEnd();
      }

      function linePoint(x, y) {
        x = Math.max(-d3_geo_clipViewMAX, Math.min(d3_geo_clipViewMAX, x));
        y = Math.max(-d3_geo_clipViewMAX, Math.min(d3_geo_clipViewMAX, y));
        var v = visible(x, y);
        if (polygon) ring.push([x, y]);

        if (first) {
          x__ = x, y__ = y, v__ = v;
          first = false;

          if (v) {
            listener.lineStart();
            listener.point(x, y);
          }
        } else {
          if (v && v_) listener.point(x, y);else {
            var a = [x_, y_],
                b = [x, y];

            if (clipLine(a, b)) {
              if (!v_) {
                listener.lineStart();
                listener.point(a[0], a[1]);
              }

              listener.point(b[0], b[1]);
              if (!v) listener.lineEnd();
            } else {
              listener.lineStart();
              listener.point(x, y);
            }
          }
        }

        x_ = x, y_ = y, v_ = v;
      }

      return clip;
    };

    function corner(p, direction) {
      return Math.abs(p[0] - x0) < ε ? direction > 0 ? 0 : 3 : Math.abs(p[0] - x1) < ε ? direction > 0 ? 2 : 1 : Math.abs(p[1] - y0) < ε ? direction > 0 ? 1 : 0 : direction > 0 ? 3 : 2;
    }

    function compare(a, b) {
      return comparePoints(a.point, b.point);
    }

    function comparePoints(a, b) {
      var ca = corner(a, 1),
          cb = corner(b, 1);
      return ca !== cb ? ca - cb : ca === 0 ? b[1] - a[1] : ca === 1 ? a[0] - b[0] : ca === 2 ? a[1] - b[1] : b[0] - a[0];
    }

    function clipLine(a, b) {
      var dx = b[0] - a[0],
          dy = b[1] - a[1],
          t = [0, 1];
      if (Math.abs(dx) < ε && Math.abs(dy) < ε) return x0 <= a[0] && a[0] <= x1 && y0 <= a[1] && a[1] <= y1;

      if (d3_geo_clipViewT(x0 - a[0], dx, t) && d3_geo_clipViewT(a[0] - x1, -dx, t) && d3_geo_clipViewT(y0 - a[1], dy, t) && d3_geo_clipViewT(a[1] - y1, -dy, t)) {
        if (t[1] < 1) {
          b[0] = a[0] + t[1] * dx;
          b[1] = a[1] + t[1] * dy;
        }

        if (t[0] > 0) {
          a[0] += t[0] * dx;
          a[1] += t[0] * dy;
        }

        return true;
      }

      return false;
    }
  }

  function d3_geo_clipViewT(num, denominator, t) {
    if (Math.abs(denominator) < ε) return num <= 0;
    var u = num / denominator;

    if (denominator > 0) {
      if (u > t[1]) return false;
      if (u > t[0]) t[0] = u;
    } else {
      if (u < t[0]) return false;
      if (u < t[1]) t[1] = u;
    }

    return true;
  }

  function d3_geo_compose(a, b) {
    function compose(x, y) {
      return x = a(x, y), b(x[0], x[1]);
    }

    if (a.invert && b.invert) compose.invert = function (x, y) {
      return x = b.invert(x, y), x && a.invert(x[0], x[1]);
    };
    return compose;
  }

  function d3_geo_resample(project) {
    var δ2 = .5,
        maxDepth = 16;

    function resample(stream) {
      var λ0, x0, y0, a0, b0, c0;
      var resample = {
        point: point,
        lineStart: lineStart,
        lineEnd: lineEnd,
        polygonStart: function polygonStart() {
          stream.polygonStart();
          resample.lineStart = polygonLineStart;
        },
        polygonEnd: function polygonEnd() {
          stream.polygonEnd();
          resample.lineStart = lineStart;
        }
      };

      function point(x, y) {
        x = project(x, y);
        stream.point(x[0], x[1]);
      }

      function lineStart() {
        x0 = NaN;
        resample.point = linePoint;
        stream.lineStart();
      }

      function linePoint(λ, φ) {
        var c = d3_geo_cartesian([λ, φ]),
            p = project(λ, φ);
        resampleLineTo(x0, y0, λ0, a0, b0, c0, x0 = p[0], y0 = p[1], λ0 = λ, a0 = c[0], b0 = c[1], c0 = c[2], maxDepth, stream);
        stream.point(x0, y0);
      }

      function lineEnd() {
        resample.point = point;
        stream.lineEnd();
      }

      function polygonLineStart() {
        var λ00, φ00, x00, y00, a00, b00, c00;
        lineStart();

        resample.point = function (λ, φ) {
          linePoint(λ00 = λ, φ00 = φ), x00 = x0, y00 = y0, a00 = a0, b00 = b0, c00 = c0;
          resample.point = linePoint;
        };

        resample.lineEnd = function () {
          resampleLineTo(x0, y0, λ0, a0, b0, c0, x00, y00, λ00, a00, b00, c00, maxDepth, stream);
          resample.lineEnd = lineEnd;
          lineEnd();
        };
      }

      return resample;
    }

    function resampleLineTo(x0, y0, λ0, a0, b0, c0, x1, y1, λ1, a1, b1, c1, depth, stream) {
      var dx = x1 - x0,
          dy = y1 - y0,
          d2 = dx * dx + dy * dy;

      if (d2 > 4 * δ2 && depth--) {
        var a = a0 + a1,
            b = b0 + b1,
            c = c0 + c1,
            m = Math.sqrt(a * a + b * b + c * c),
            φ2 = Math.asin(c /= m),
            λ2 = Math.abs(Math.abs(c) - 1) < ε ? (λ0 + λ1) / 2 : Math.atan2(b, a),
            p = project(λ2, φ2),
            x2 = p[0],
            y2 = p[1],
            dx2 = x2 - x0,
            dy2 = y2 - y0,
            dz = dy * dx2 - dx * dy2;

        if (dz * dz / d2 > δ2 || Math.abs((dx * dx2 + dy * dy2) / d2 - .5) > .3) {
          resampleLineTo(x0, y0, λ0, a0, b0, c0, x2, y2, λ2, a /= m, b /= m, c, depth, stream);
          stream.point(x2, y2);
          resampleLineTo(x2, y2, λ2, a, b, c, x1, y1, λ1, a1, b1, c1, depth, stream);
        }
      }
    }

    resample.precision = function (_) {
      if (!arguments.length) return Math.sqrt(δ2);
      maxDepth = (δ2 = _ * _) > 0 && 16;
      return resample;
    };

    return resample;
  }

  d3.geo.projection = d3_geo_projection;
  d3.geo.projectionMutator = d3_geo_projectionMutator;

  function d3_geo_projection(project) {
    return d3_geo_projectionMutator(function () {
      return project;
    })();
  }

  function d3_geo_projectionMutator(projectAt) {
    var project,
        rotate,
        projectRotate,
        projectResample = d3_geo_resample(function (x, y) {
      x = project(x, y);
      return [x[0] * k + δx, δy - x[1] * k];
    }),
        k = 150,
        x = 480,
        y = 250,
        λ = 0,
        φ = 0,
        δλ = 0,
        δφ = 0,
        δγ = 0,
        δx,
        δy,
        preclip = d3_geo_clipAntimeridian,
        postclip = d3_identity,
        clipAngle = null,
        clipExtent = null;

    function projection(point) {
      point = projectRotate(point[0] * d3_radians, point[1] * d3_radians);
      return [point[0] * k + δx, δy - point[1] * k];
    }

    function invert(point) {
      point = projectRotate.invert((point[0] - δx) / k, (δy - point[1]) / k);
      return point && [point[0] * d3_degrees, point[1] * d3_degrees];
    }

    projection.stream = function (stream) {
      return d3_geo_projectionRadiansRotate(rotate, preclip(projectResample(postclip(stream))));
    };

    projection.clipAngle = function (_) {
      if (!arguments.length) return clipAngle;
      preclip = _ == null ? (clipAngle = _, d3_geo_clipAntimeridian) : d3_geo_clipCircle((clipAngle = +_) * d3_radians);
      return projection;
    };

    projection.clipExtent = function (_) {
      if (!arguments.length) return clipExtent;
      clipExtent = _;
      postclip = _ == null ? d3_identity : d3_geo_clipView(_[0][0], _[0][1], _[1][0], _[1][1]);
      return projection;
    };

    projection.scale = function (_) {
      if (!arguments.length) return k;
      k = +_;
      return reset();
    };

    projection.translate = function (_) {
      if (!arguments.length) return [x, y];
      x = +_[0];
      y = +_[1];
      return reset();
    };

    projection.center = function (_) {
      if (!arguments.length) return [λ * d3_degrees, φ * d3_degrees];
      λ = _[0] % 360 * d3_radians;
      φ = _[1] % 360 * d3_radians;
      return reset();
    };

    projection.rotate = function (_) {
      if (!arguments.length) return [δλ * d3_degrees, δφ * d3_degrees, δγ * d3_degrees];
      δλ = _[0] % 360 * d3_radians;
      δφ = _[1] % 360 * d3_radians;
      δγ = _.length > 2 ? _[2] % 360 * d3_radians : 0;
      return reset();
    };

    d3.rebind(projection, projectResample, "precision");

    function reset() {
      projectRotate = d3_geo_compose(rotate = d3_geo_rotation(δλ, δφ, δγ), project);
      var center = project(λ, φ);
      δx = x - center[0] * k;
      δy = y + center[1] * k;
      return projection;
    }

    return function () {
      project = projectAt.apply(this, arguments);
      projection.invert = project.invert && invert;
      return reset();
    };
  }

  function d3_geo_projectionRadiansRotate(rotate, stream) {
    return {
      point: function point(x, y) {
        y = rotate(x * d3_radians, y * d3_radians), x = y[0];
        stream.point(x > π ? x - 2 * π : x < -π ? x + 2 * π : x, y[1]);
      },
      sphere: function sphere() {
        stream.sphere();
      },
      lineStart: function lineStart() {
        stream.lineStart();
      },
      lineEnd: function lineEnd() {
        stream.lineEnd();
      },
      polygonStart: function polygonStart() {
        stream.polygonStart();
      },
      polygonEnd: function polygonEnd() {
        stream.polygonEnd();
      }
    };
  }

  function d3_geo_equirectangular(λ, φ) {
    return [λ, φ];
  }

  (d3.geo.equirectangular = function () {
    return d3_geo_projection(d3_geo_equirectangular);
  }).raw = d3_geo_equirectangular.invert = d3_geo_equirectangular;

  d3.geo.rotation = function (rotate) {
    rotate = d3_geo_rotation(rotate[0] % 360 * d3_radians, rotate[1] * d3_radians, rotate.length > 2 ? rotate[2] * d3_radians : 0);

    function forward(coordinates) {
      coordinates = rotate(coordinates[0] * d3_radians, coordinates[1] * d3_radians);
      return coordinates[0] *= d3_degrees, coordinates[1] *= d3_degrees, coordinates;
    }

    forward.invert = function (coordinates) {
      coordinates = rotate.invert(coordinates[0] * d3_radians, coordinates[1] * d3_radians);
      return coordinates[0] *= d3_degrees, coordinates[1] *= d3_degrees, coordinates;
    };

    return forward;
  };

  function d3_geo_rotation(δλ, δφ, δγ) {
    return δλ ? δφ || δγ ? d3_geo_compose(d3_geo_rotationλ(δλ), d3_geo_rotationφγ(δφ, δγ)) : d3_geo_rotationλ(δλ) : δφ || δγ ? d3_geo_rotationφγ(δφ, δγ) : d3_geo_equirectangular;
  }

  function d3_geo_forwardRotationλ(δλ) {
    return function (λ, φ) {
      return λ += δλ, [λ > π ? λ - 2 * π : λ < -π ? λ + 2 * π : λ, φ];
    };
  }

  function d3_geo_rotationλ(δλ) {
    var rotation = d3_geo_forwardRotationλ(δλ);
    rotation.invert = d3_geo_forwardRotationλ(-δλ);
    return rotation;
  }

  function d3_geo_rotationφγ(δφ, δγ) {
    var cosδφ = Math.cos(δφ),
        sinδφ = Math.sin(δφ),
        cosδγ = Math.cos(δγ),
        sinδγ = Math.sin(δγ);

    function rotation(λ, φ) {
      var cosφ = Math.cos(φ),
          x = Math.cos(λ) * cosφ,
          y = Math.sin(λ) * cosφ,
          z = Math.sin(φ),
          k = z * cosδφ + x * sinδφ;
      return [Math.atan2(y * cosδγ - k * sinδγ, x * cosδφ - z * sinδφ), Math.asin(Math.max(-1, Math.min(1, k * cosδγ + y * sinδγ)))];
    }

    rotation.invert = function (λ, φ) {
      var cosφ = Math.cos(φ),
          x = Math.cos(λ) * cosφ,
          y = Math.sin(λ) * cosφ,
          z = Math.sin(φ),
          k = z * cosδγ - y * sinδγ;
      return [Math.atan2(y * cosδγ + z * sinδγ, x * cosδφ + k * sinδφ), Math.asin(Math.max(-1, Math.min(1, k * cosδφ - x * sinδφ)))];
    };

    return rotation;
  }

  d3.geo.circle = function () {
    var origin = [0, 0],
        angle,
        precision = 6,
        interpolate;

    function circle() {
      var center = typeof origin === "function" ? origin.apply(this, arguments) : origin,
          rotate = d3_geo_rotation(-center[0] * d3_radians, -center[1] * d3_radians, 0).invert,
          ring = [];
      interpolate(null, null, 1, {
        point: function point(x, y) {
          ring.push(x = rotate(x, y));
          x[0] *= d3_degrees, x[1] *= d3_degrees;
        }
      });
      return {
        type: "Polygon",
        coordinates: [ring]
      };
    }

    circle.origin = function (x) {
      if (!arguments.length) return origin;
      origin = x;
      return circle;
    };

    circle.angle = function (x) {
      if (!arguments.length) return angle;
      interpolate = d3_geo_circleInterpolate((angle = +x) * d3_radians, precision * d3_radians);
      return circle;
    };

    circle.precision = function (_) {
      if (!arguments.length) return precision;
      interpolate = d3_geo_circleInterpolate(angle * d3_radians, (precision = +_) * d3_radians);
      return circle;
    };

    return circle.angle(90);
  };

  function d3_geo_circleInterpolate(radius, precision) {
    var cr = Math.cos(radius),
        sr = Math.sin(radius);
    return function (from, to, direction, listener) {
      if (from != null) {
        from = d3_geo_circleAngle(cr, from);
        to = d3_geo_circleAngle(cr, to);
        if (direction > 0 ? from < to : from > to) from += direction * 2 * π;
      } else {
        from = radius + direction * 2 * π;
        to = radius;
      }

      var point;

      for (var step = direction * precision, t = from; direction > 0 ? t > to : t < to; t -= step) {
        listener.point((point = d3_geo_spherical([cr, -sr * Math.cos(t), -sr * Math.sin(t)]))[0], point[1]);
      }
    };
  }

  function d3_geo_circleAngle(cr, point) {
    var a = d3_geo_cartesian(point);
    a[0] -= cr;
    d3_geo_cartesianNormalize(a);
    var angle = d3_acos(-a[1]);
    return ((-a[2] < 0 ? -angle : angle) + 2 * Math.PI - ε) % (2 * Math.PI);
  }

  d3.geo.distance = function (a, b) {
    var Δλ = (b[0] - a[0]) * d3_radians,
        φ0 = a[1] * d3_radians,
        φ1 = b[1] * d3_radians,
        sinΔλ = Math.sin(Δλ),
        cosΔλ = Math.cos(Δλ),
        sinφ0 = Math.sin(φ0),
        cosφ0 = Math.cos(φ0),
        sinφ1 = Math.sin(φ1),
        cosφ1 = Math.cos(φ1),
        t;
    return Math.atan2(Math.sqrt((t = cosφ1 * sinΔλ) * t + (t = cosφ0 * sinφ1 - sinφ0 * cosφ1 * cosΔλ) * t), sinφ0 * sinφ1 + cosφ0 * cosφ1 * cosΔλ);
  };

  d3.geo.graticule = function () {
    var x1,
        x0,
        X1,
        X0,
        y1,
        y0,
        Y1,
        Y0,
        dx = 10,
        dy = dx,
        DX = 90,
        DY = 360,
        x,
        y,
        X,
        Y,
        precision = 2.5;

    function graticule() {
      return {
        type: "MultiLineString",
        coordinates: lines()
      };
    }

    function lines() {
      return d3.range(Math.ceil(X0 / DX) * DX, X1, DX).map(X).concat(d3.range(Math.ceil(Y0 / DY) * DY, Y1, DY).map(Y)).concat(d3.range(Math.ceil(x0 / dx) * dx, x1, dx).filter(function (x) {
        return Math.abs(x % DX) > ε;
      }).map(x)).concat(d3.range(Math.ceil(y0 / dy) * dy, y1, dy).filter(function (y) {
        return Math.abs(y % DY) > ε;
      }).map(y));
    }

    graticule.lines = function () {
      return lines().map(function (coordinates) {
        return {
          type: "LineString",
          coordinates: coordinates
        };
      });
    };

    graticule.outline = function () {
      return {
        type: "Polygon",
        coordinates: [X(X0).concat(Y(Y1).slice(1), X(X1).reverse().slice(1), Y(Y0).reverse().slice(1))]
      };
    };

    graticule.extent = function (_) {
      if (!arguments.length) return graticule.minorExtent();
      return graticule.majorExtent(_).minorExtent(_);
    };

    graticule.majorExtent = function (_) {
      if (!arguments.length) return [[X0, Y0], [X1, Y1]];
      X0 = +_[0][0], X1 = +_[1][0];
      Y0 = +_[0][1], Y1 = +_[1][1];
      if (X0 > X1) _ = X0, X0 = X1, X1 = _;
      if (Y0 > Y1) _ = Y0, Y0 = Y1, Y1 = _;
      return graticule.precision(precision);
    };

    graticule.minorExtent = function (_) {
      if (!arguments.length) return [[x0, y0], [x1, y1]];
      x0 = +_[0][0], x1 = +_[1][0];
      y0 = +_[0][1], y1 = +_[1][1];
      if (x0 > x1) _ = x0, x0 = x1, x1 = _;
      if (y0 > y1) _ = y0, y0 = y1, y1 = _;
      return graticule.precision(precision);
    };

    graticule.step = function (_) {
      if (!arguments.length) return graticule.minorStep();
      return graticule.majorStep(_).minorStep(_);
    };

    graticule.majorStep = function (_) {
      if (!arguments.length) return [DX, DY];
      DX = +_[0], DY = +_[1];
      return graticule;
    };

    graticule.minorStep = function (_) {
      if (!arguments.length) return [dx, dy];
      dx = +_[0], dy = +_[1];
      return graticule;
    };

    graticule.precision = function (_) {
      if (!arguments.length) return precision;
      precision = +_;
      x = d3_geo_graticuleX(y0, y1, 90);
      y = d3_geo_graticuleY(x0, x1, precision);
      X = d3_geo_graticuleX(Y0, Y1, 90);
      Y = d3_geo_graticuleY(X0, X1, precision);
      return graticule;
    };

    return graticule.majorExtent([[-180, -90 + ε], [180, 90 - ε]]).minorExtent([[-180, -80 - ε], [180, 80 + ε]]);
  };

  function d3_geo_graticuleX(y0, y1, dy) {
    var y = d3.range(y0, y1 - ε, dy).concat(y1);
    return function (x) {
      return y.map(function (y) {
        return [x, y];
      });
    };
  }

  function d3_geo_graticuleY(x0, x1, dx) {
    var x = d3.range(x0, x1 - ε, dx).concat(x1);
    return function (y) {
      return x.map(function (x) {
        return [x, y];
      });
    };
  }

  function d3_source(d) {
    return d.source;
  }

  function d3_target(d) {
    return d.target;
  }

  d3.geo.greatArc = function () {
    var source = d3_source,
        source_,
        target = d3_target,
        target_;

    function greatArc() {
      return {
        type: "LineString",
        coordinates: [source_ || source.apply(this, arguments), target_ || target.apply(this, arguments)]
      };
    }

    greatArc.distance = function () {
      return d3.geo.distance(source_ || source.apply(this, arguments), target_ || target.apply(this, arguments));
    };

    greatArc.source = function (_) {
      if (!arguments.length) return source;
      source = _, source_ = typeof _ === "function" ? null : _;
      return greatArc;
    };

    greatArc.target = function (_) {
      if (!arguments.length) return target;
      target = _, target_ = typeof _ === "function" ? null : _;
      return greatArc;
    };

    greatArc.precision = function () {
      return arguments.length ? greatArc : 0;
    };

    return greatArc;
  };

  d3.geo.interpolate = function (source, target) {
    return d3_geo_interpolate(source[0] * d3_radians, source[1] * d3_radians, target[0] * d3_radians, target[1] * d3_radians);
  };

  function d3_geo_interpolate(x0, y0, x1, y1) {
    var cy0 = Math.cos(y0),
        sy0 = Math.sin(y0),
        cy1 = Math.cos(y1),
        sy1 = Math.sin(y1),
        kx0 = cy0 * Math.cos(x0),
        ky0 = cy0 * Math.sin(x0),
        kx1 = cy1 * Math.cos(x1),
        ky1 = cy1 * Math.sin(x1),
        d = 2 * Math.asin(Math.sqrt(d3_haversin(y1 - y0) + cy0 * cy1 * d3_haversin(x1 - x0))),
        k = 1 / Math.sin(d);
    var interpolate = d ? function (t) {
      var B = Math.sin(t *= d) * k,
          A = Math.sin(d - t) * k,
          x = A * kx0 + B * kx1,
          y = A * ky0 + B * ky1,
          z = A * sy0 + B * sy1;
      return [Math.atan2(y, x) * d3_degrees, Math.atan2(z, Math.sqrt(x * x + y * y)) * d3_degrees];
    } : function () {
      return [x0 * d3_degrees, y0 * d3_degrees];
    };
    interpolate.distance = d;
    return interpolate;
  }

  d3.geo.length = function (object) {
    d3_geo_lengthSum = 0;
    d3.geo.stream(object, d3_geo_length);
    return d3_geo_lengthSum;
  };

  var d3_geo_lengthSum;
  var d3_geo_length = {
    sphere: d3_noop,
    point: d3_noop,
    lineStart: d3_geo_lengthLineStart,
    lineEnd: d3_noop,
    polygonStart: d3_noop,
    polygonEnd: d3_noop
  };

  function d3_geo_lengthLineStart() {
    var λ0, sinφ0, cosφ0;

    d3_geo_length.point = function (λ, φ) {
      λ0 = λ * d3_radians, sinφ0 = Math.sin(φ *= d3_radians), cosφ0 = Math.cos(φ);
      d3_geo_length.point = nextPoint;
    };

    d3_geo_length.lineEnd = function () {
      d3_geo_length.point = d3_geo_length.lineEnd = d3_noop;
    };

    function nextPoint(λ, φ) {
      var sinφ = Math.sin(φ *= d3_radians),
          cosφ = Math.cos(φ),
          t = Math.abs((λ *= d3_radians) - λ0),
          cosΔλ = Math.cos(t);
      d3_geo_lengthSum += Math.atan2(Math.sqrt((t = cosφ * Math.sin(t)) * t + (t = cosφ0 * sinφ - sinφ0 * cosφ * cosΔλ) * t), sinφ0 * sinφ + cosφ0 * cosφ * cosΔλ);
      λ0 = λ, sinφ0 = sinφ, cosφ0 = cosφ;
    }
  }

  function d3_geo_conic(projectAt) {
    var φ0 = 0,
        φ1 = π / 3,
        m = d3_geo_projectionMutator(projectAt),
        p = m(φ0, φ1);

    p.parallels = function (_) {
      if (!arguments.length) return [φ0 / π * 180, φ1 / π * 180];
      return m(φ0 = _[0] * π / 180, φ1 = _[1] * π / 180);
    };

    return p;
  }

  function d3_geo_conicEqualArea(φ0, φ1) {
    var sinφ0 = Math.sin(φ0),
        n = (sinφ0 + Math.sin(φ1)) / 2,
        C = 1 + sinφ0 * (2 * n - sinφ0),
        ρ0 = Math.sqrt(C) / n;

    function forward(λ, φ) {
      var ρ = Math.sqrt(C - 2 * n * Math.sin(φ)) / n;
      return [ρ * Math.sin(λ *= n), ρ0 - ρ * Math.cos(λ)];
    }

    forward.invert = function (x, y) {
      var ρ0_y = ρ0 - y;
      return [Math.atan2(x, ρ0_y) / n, Math.asin((C - (x * x + ρ0_y * ρ0_y) * n * n) / (2 * n))];
    };

    return forward;
  }

  (d3.geo.conicEqualArea = function () {
    return d3_geo_conic(d3_geo_conicEqualArea);
  }).raw = d3_geo_conicEqualArea;

  d3.geo.albersUsa = function () {
    var lower48 = d3.geo.conicEqualArea().rotate([98, 0]).center([0, 38]).parallels([29.5, 45.5]);
    var alaska = d3.geo.conicEqualArea().rotate([160, 0]).center([0, 60]).parallels([55, 65]);
    var hawaii = d3.geo.conicEqualArea().rotate([160, 0]).center([0, 20]).parallels([8, 18]);
    var puertoRico = d3.geo.conicEqualArea().rotate([60, 0]).center([0, 10]).parallels([8, 18]);
    var alaskaInvert, hawaiiInvert, puertoRicoInvert;

    function albersUsa(coordinates) {
      return projection(coordinates)(coordinates);
    }

    function projection(point) {
      var lon = point[0],
          lat = point[1];
      return lat > 50 ? alaska : lon < -140 ? hawaii : lat < 21 ? puertoRico : lower48;
    }

    albersUsa.invert = function (coordinates) {
      return alaskaInvert(coordinates) || hawaiiInvert(coordinates) || puertoRicoInvert(coordinates) || lower48.invert(coordinates);
    };

    albersUsa.scale = function (x) {
      if (!arguments.length) return lower48.scale();
      lower48.scale(x);
      alaska.scale(x * .6);
      hawaii.scale(x);
      puertoRico.scale(x * 1.5);
      return albersUsa.translate(lower48.translate());
    };

    albersUsa.translate = function (x) {
      if (!arguments.length) return lower48.translate();
      var dz = lower48.scale(),
          dx = x[0],
          dy = x[1];
      lower48.translate(x);
      alaska.translate([dx - .4 * dz, dy + .17 * dz]);
      hawaii.translate([dx - .19 * dz, dy + .2 * dz]);
      puertoRico.translate([dx + .58 * dz, dy + .43 * dz]);
      alaskaInvert = d3_geo_albersUsaInvert(alaska, [[-180, 50], [-130, 72]]);
      hawaiiInvert = d3_geo_albersUsaInvert(hawaii, [[-164, 18], [-154, 24]]);
      puertoRicoInvert = d3_geo_albersUsaInvert(puertoRico, [[-67.5, 17.5], [-65, 19]]);
      return albersUsa;
    };

    return albersUsa.scale(1e3);
  };

  function d3_geo_albersUsaInvert(projection, extent) {
    var a = projection(extent[0]),
        b = projection([.5 * (extent[0][0] + extent[1][0]), extent[0][1]]),
        c = projection([extent[1][0], extent[0][1]]),
        d = projection(extent[1]);
    var dya = b[1] - a[1],
        dxa = b[0] - a[0],
        dyb = c[1] - b[1],
        dxb = c[0] - b[0];
    var ma = dya / dxa,
        mb = dyb / dxb;
    var cx = .5 * (ma * mb * (a[1] - c[1]) + mb * (a[0] + b[0]) - ma * (b[0] + c[0])) / (mb - ma),
        cy = (.5 * (a[0] + b[0]) - cx) / ma + .5 * (a[1] + b[1]);
    var dx0 = d[0] - cx,
        dy0 = d[1] - cy,
        dx1 = a[0] - cx,
        dy1 = a[1] - cy,
        r0 = dx0 * dx0 + dy0 * dy0,
        r1 = dx1 * dx1 + dy1 * dy1;
    var a0 = Math.atan2(dy0, dx0),
        a1 = Math.atan2(dy1, dx1);
    return function (coordinates) {
      var dx = coordinates[0] - cx,
          dy = coordinates[1] - cy,
          r = dx * dx + dy * dy,
          a = Math.atan2(dy, dx);
      if (r0 < r && r < r1 && a0 < a && a < a1) return projection.invert(coordinates);
    };
  }

  var d3_geo_pathAreaSum,
      d3_geo_pathAreaPolygon,
      d3_geo_pathArea = {
    point: d3_noop,
    lineStart: d3_noop,
    lineEnd: d3_noop,
    polygonStart: function polygonStart() {
      d3_geo_pathAreaPolygon = 0;
      d3_geo_pathArea.lineStart = d3_geo_pathAreaRingStart;
    },
    polygonEnd: function polygonEnd() {
      d3_geo_pathArea.lineStart = d3_geo_pathArea.lineEnd = d3_geo_pathArea.point = d3_noop;
      d3_geo_pathAreaSum += Math.abs(d3_geo_pathAreaPolygon / 2);
    }
  };

  function d3_geo_pathAreaRingStart() {
    var x00, y00, x0, y0;

    d3_geo_pathArea.point = function (x, y) {
      d3_geo_pathArea.point = nextPoint;
      x00 = x0 = x, y00 = y0 = y;
    };

    function nextPoint(x, y) {
      d3_geo_pathAreaPolygon += y0 * x - x0 * y;
      x0 = x, y0 = y;
    }

    d3_geo_pathArea.lineEnd = function () {
      nextPoint(x00, y00);
    };
  }

  function d3_geo_pathBuffer() {
    var pointCircle = d3_geo_pathCircle(4.5),
        buffer = [];
    var stream = {
      point: point,
      lineStart: function lineStart() {
        stream.point = pointLineStart;
      },
      lineEnd: lineEnd,
      polygonStart: function polygonStart() {
        stream.lineEnd = lineEndPolygon;
      },
      polygonEnd: function polygonEnd() {
        stream.lineEnd = lineEnd;
        stream.point = point;
      },
      pointRadius: function pointRadius(_) {
        pointCircle = d3_geo_pathCircle(_);
        return stream;
      },
      result: function result() {
        if (buffer.length) {
          var result = buffer.join("");
          buffer = [];
          return result;
        }
      }
    };

    function point(x, y) {
      buffer.push("M", x, ",", y, pointCircle);
    }

    function pointLineStart(x, y) {
      buffer.push("M", x, ",", y);
      stream.point = pointLine;
    }

    function pointLine(x, y) {
      buffer.push("L", x, ",", y);
    }

    function lineEnd() {
      stream.point = point;
    }

    function lineEndPolygon() {
      buffer.push("Z");
    }

    return stream;
  }

  var d3_geo_pathCentroid = {
    point: d3_geo_pathCentroidPoint,
    lineStart: d3_geo_pathCentroidLineStart,
    lineEnd: d3_geo_pathCentroidLineEnd,
    polygonStart: function polygonStart() {
      d3_geo_pathCentroid.lineStart = d3_geo_pathCentroidRingStart;
    },
    polygonEnd: function polygonEnd() {
      d3_geo_pathCentroid.point = d3_geo_pathCentroidPoint;
      d3_geo_pathCentroid.lineStart = d3_geo_pathCentroidLineStart;
      d3_geo_pathCentroid.lineEnd = d3_geo_pathCentroidLineEnd;
    }
  };

  function d3_geo_pathCentroidPoint(x, y) {
    if (d3_geo_centroidDimension) return;
    d3_geo_centroidX += x;
    d3_geo_centroidY += y;
    ++d3_geo_centroidZ;
  }

  function d3_geo_pathCentroidLineStart() {
    var x0, y0;

    if (d3_geo_centroidDimension !== 1) {
      if (d3_geo_centroidDimension < 1) {
        d3_geo_centroidDimension = 1;
        d3_geo_centroidX = d3_geo_centroidY = d3_geo_centroidZ = 0;
      } else return;
    }

    d3_geo_pathCentroid.point = function (x, y) {
      d3_geo_pathCentroid.point = nextPoint;
      x0 = x, y0 = y;
    };

    function nextPoint(x, y) {
      var dx = x - x0,
          dy = y - y0,
          z = Math.sqrt(dx * dx + dy * dy);
      d3_geo_centroidX += z * (x0 + x) / 2;
      d3_geo_centroidY += z * (y0 + y) / 2;
      d3_geo_centroidZ += z;
      x0 = x, y0 = y;
    }
  }

  function d3_geo_pathCentroidLineEnd() {
    d3_geo_pathCentroid.point = d3_geo_pathCentroidPoint;
  }

  function d3_geo_pathCentroidRingStart() {
    var x00, y00, x0, y0;

    if (d3_geo_centroidDimension < 2) {
      d3_geo_centroidDimension = 2;
      d3_geo_centroidX = d3_geo_centroidY = d3_geo_centroidZ = 0;
    }

    d3_geo_pathCentroid.point = function (x, y) {
      d3_geo_pathCentroid.point = nextPoint;
      x00 = x0 = x, y00 = y0 = y;
    };

    function nextPoint(x, y) {
      var z = y0 * x - x0 * y;
      d3_geo_centroidX += z * (x0 + x);
      d3_geo_centroidY += z * (y0 + y);
      d3_geo_centroidZ += z * 3;
      x0 = x, y0 = y;
    }

    d3_geo_pathCentroid.lineEnd = function () {
      nextPoint(x00, y00);
    };
  }

  function d3_geo_pathContext(context) {
    var _pointRadius = 4.5;
    var stream = {
      point: point,
      lineStart: function lineStart() {
        stream.point = pointLineStart;
      },
      lineEnd: lineEnd,
      polygonStart: function polygonStart() {
        stream.lineEnd = lineEndPolygon;
      },
      polygonEnd: function polygonEnd() {
        stream.lineEnd = lineEnd;
        stream.point = point;
      },
      pointRadius: function pointRadius(_) {
        _pointRadius = _;
        return stream;
      },
      result: d3_noop
    };

    function point(x, y) {
      context.moveTo(x, y);
      context.arc(x, y, _pointRadius, 0, 2 * π);
    }

    function pointLineStart(x, y) {
      context.moveTo(x, y);
      stream.point = pointLine;
    }

    function pointLine(x, y) {
      context.lineTo(x, y);
    }

    function lineEnd() {
      stream.point = point;
    }

    function lineEndPolygon() {
      context.closePath();
    }

    return stream;
  }

  d3.geo.path = function () {
    var pointRadius = 4.5,
        projection,
        context,
        projectStream,
        contextStream;

    function path(object) {
      if (object) d3.geo.stream(object, projectStream(contextStream.pointRadius(typeof pointRadius === "function" ? +pointRadius.apply(this, arguments) : pointRadius)));
      return contextStream.result();
    }

    path.area = function (object) {
      d3_geo_pathAreaSum = 0;
      d3.geo.stream(object, projectStream(d3_geo_pathArea));
      return d3_geo_pathAreaSum;
    };

    path.centroid = function (object) {
      d3_geo_centroidDimension = d3_geo_centroidX = d3_geo_centroidY = d3_geo_centroidZ = 0;
      d3.geo.stream(object, projectStream(d3_geo_pathCentroid));
      return d3_geo_centroidZ ? [d3_geo_centroidX / d3_geo_centroidZ, d3_geo_centroidY / d3_geo_centroidZ] : undefined;
    };

    path.bounds = function (object) {
      return d3_geo_bounds(projectStream)(object);
    };

    path.projection = function (_) {
      if (!arguments.length) return projection;
      projectStream = (projection = _) ? _.stream || d3_geo_pathProjectStream(_) : d3_identity;
      return path;
    };

    path.context = function (_) {
      if (!arguments.length) return context;
      contextStream = (context = _) == null ? new d3_geo_pathBuffer() : new d3_geo_pathContext(_);
      return path;
    };

    path.pointRadius = function (_) {
      if (!arguments.length) return pointRadius;
      pointRadius = typeof _ === "function" ? _ : +_;
      return path;
    };

    return path.projection(d3.geo.albersUsa()).context(null);
  };

  function d3_geo_pathCircle(radius) {
    return "m0," + radius + "a" + radius + "," + radius + " 0 1,1 0," + -2 * radius + "a" + radius + "," + radius + " 0 1,1 0," + +2 * radius + "z";
  }

  function d3_geo_pathProjectStream(project) {
    var resample = d3_geo_resample(function (λ, φ) {
      return project([λ * d3_degrees, φ * d3_degrees]);
    });
    return function (stream) {
      stream = resample(stream);
      return {
        point: function point(λ, φ) {
          stream.point(λ * d3_radians, φ * d3_radians);
        },
        sphere: function sphere() {
          stream.sphere();
        },
        lineStart: function lineStart() {
          stream.lineStart();
        },
        lineEnd: function lineEnd() {
          stream.lineEnd();
        },
        polygonStart: function polygonStart() {
          stream.polygonStart();
        },
        polygonEnd: function polygonEnd() {
          stream.polygonEnd();
        }
      };
    };
  }

  d3.geo.albers = function () {
    return d3.geo.conicEqualArea().parallels([29.5, 45.5]).rotate([98, 0]).center([0, 38]).scale(1e3);
  };

  function d3_geo_azimuthal(scale, angle) {
    function azimuthal(λ, φ) {
      var cosλ = Math.cos(λ),
          cosφ = Math.cos(φ),
          k = scale(cosλ * cosφ);
      return [k * cosφ * Math.sin(λ), k * Math.sin(φ)];
    }

    azimuthal.invert = function (x, y) {
      var ρ = Math.sqrt(x * x + y * y),
          c = angle(ρ),
          sinc = Math.sin(c),
          cosc = Math.cos(c);
      return [Math.atan2(x * sinc, ρ * cosc), Math.asin(ρ && y * sinc / ρ)];
    };

    return azimuthal;
  }

  var d3_geo_azimuthalEqualArea = d3_geo_azimuthal(function (cosλcosφ) {
    return Math.sqrt(2 / (1 + cosλcosφ));
  }, function (ρ) {
    return 2 * Math.asin(ρ / 2);
  });
  (d3.geo.azimuthalEqualArea = function () {
    return d3_geo_projection(d3_geo_azimuthalEqualArea);
  }).raw = d3_geo_azimuthalEqualArea;
  var d3_geo_azimuthalEquidistant = d3_geo_azimuthal(function (cosλcosφ) {
    var c = Math.acos(cosλcosφ);
    return c && c / Math.sin(c);
  }, d3_identity);
  (d3.geo.azimuthalEquidistant = function () {
    return d3_geo_projection(d3_geo_azimuthalEquidistant);
  }).raw = d3_geo_azimuthalEquidistant;

  function d3_geo_conicConformal(φ0, φ1) {
    var cosφ0 = Math.cos(φ0),
        t = function t(φ) {
      return Math.tan(π / 4 + φ / 2);
    },
        n = φ0 === φ1 ? Math.sin(φ0) : Math.log(cosφ0 / Math.cos(φ1)) / Math.log(t(φ1) / t(φ0)),
        F = cosφ0 * Math.pow(t(φ0), n) / n;

    if (!n) return d3_geo_mercator;

    function forward(λ, φ) {
      var ρ = Math.abs(Math.abs(φ) - π / 2) < ε ? 0 : F / Math.pow(t(φ), n);
      return [ρ * Math.sin(n * λ), F - ρ * Math.cos(n * λ)];
    }

    forward.invert = function (x, y) {
      var ρ0_y = F - y,
          ρ = d3_sgn(n) * Math.sqrt(x * x + ρ0_y * ρ0_y);
      return [Math.atan2(x, ρ0_y) / n, 2 * Math.atan(Math.pow(F / ρ, 1 / n)) - π / 2];
    };

    return forward;
  }

  (d3.geo.conicConformal = function () {
    return d3_geo_conic(d3_geo_conicConformal);
  }).raw = d3_geo_conicConformal;

  function d3_geo_conicEquidistant(φ0, φ1) {
    var cosφ0 = Math.cos(φ0),
        n = φ0 === φ1 ? Math.sin(φ0) : (cosφ0 - Math.cos(φ1)) / (φ1 - φ0),
        G = cosφ0 / n + φ0;
    if (Math.abs(n) < ε) return d3_geo_equirectangular;

    function forward(λ, φ) {
      var ρ = G - φ;
      return [ρ * Math.sin(n * λ), G - ρ * Math.cos(n * λ)];
    }

    forward.invert = function (x, y) {
      var ρ0_y = G - y;
      return [Math.atan2(x, ρ0_y) / n, G - d3_sgn(n) * Math.sqrt(x * x + ρ0_y * ρ0_y)];
    };

    return forward;
  }

  (d3.geo.conicEquidistant = function () {
    return d3_geo_conic(d3_geo_conicEquidistant);
  }).raw = d3_geo_conicEquidistant;
  var d3_geo_gnomonic = d3_geo_azimuthal(function (cosλcosφ) {
    return 1 / cosλcosφ;
  }, Math.atan);
  (d3.geo.gnomonic = function () {
    return d3_geo_projection(d3_geo_gnomonic);
  }).raw = d3_geo_gnomonic;

  function d3_geo_mercator(λ, φ) {
    return [λ, Math.log(Math.tan(π / 4 + φ / 2))];
  }

  d3_geo_mercator.invert = function (x, y) {
    return [x, 2 * Math.atan(Math.exp(y)) - π / 2];
  };

  function d3_geo_mercatorProjection(project) {
    var m = d3_geo_projection(project),
        scale = m.scale,
        translate = m.translate,
        clipExtent = m.clipExtent,
        clipAuto;

    m.scale = function () {
      var v = scale.apply(m, arguments);
      return v === m ? clipAuto ? m.clipExtent(null) : m : v;
    };

    m.translate = function () {
      var v = translate.apply(m, arguments);
      return v === m ? clipAuto ? m.clipExtent(null) : m : v;
    };

    m.clipExtent = function (_) {
      var v = clipExtent.apply(m, arguments);

      if (v === m) {
        if (clipAuto = _ == null) {
          var k = π * scale(),
              t = translate();
          clipExtent([[t[0] - k, t[1] - k], [t[0] + k, t[1] + k]]);
        }
      } else if (clipAuto) {
        v = null;
      }

      return v;
    };

    return m.clipExtent(null);
  }

  (d3.geo.mercator = function () {
    return d3_geo_mercatorProjection(d3_geo_mercator);
  }).raw = d3_geo_mercator;
  var d3_geo_orthographic = d3_geo_azimuthal(function () {
    return 1;
  }, Math.asin);
  (d3.geo.orthographic = function () {
    return d3_geo_projection(d3_geo_orthographic);
  }).raw = d3_geo_orthographic;
  var d3_geo_stereographic = d3_geo_azimuthal(function (cosλcosφ) {
    return 1 / (1 + cosλcosφ);
  }, function (ρ) {
    return 2 * Math.atan(ρ);
  });
  (d3.geo.stereographic = function () {
    return d3_geo_projection(d3_geo_stereographic);
  }).raw = d3_geo_stereographic;

  function d3_geo_transverseMercator(λ, φ) {
    var B = Math.cos(φ) * Math.sin(λ);
    return [Math.log((1 + B) / (1 - B)) / 2, Math.atan2(Math.tan(φ), Math.cos(λ))];
  }

  d3_geo_transverseMercator.invert = function (x, y) {
    return [Math.atan2(d3_sinh(x), Math.cos(y)), d3_asin(Math.sin(y) / d3_cosh(x))];
  };

  (d3.geo.transverseMercator = function () {
    return d3_geo_mercatorProjection(d3_geo_transverseMercator);
  }).raw = d3_geo_transverseMercator;
  d3.geom = {};
  d3.svg = {};

  function d3_svg_line(projection) {
    var x = d3_svg_lineX,
        y = d3_svg_lineY,
        defined = d3_true,
        interpolate = d3_svg_lineLinear,
        interpolateKey = interpolate.key,
        tension = .7;

    function line(data) {
      var segments = [],
          points = [],
          i = -1,
          n = data.length,
          d,
          fx = d3_functor(x),
          fy = d3_functor(y);

      function segment() {
        segments.push("M", interpolate(projection(points), tension));
      }

      while (++i < n) {
        if (defined.call(this, d = data[i], i)) {
          points.push([+fx.call(this, d, i), +fy.call(this, d, i)]);
        } else if (points.length) {
          segment();
          points = [];
        }
      }

      if (points.length) segment();
      return segments.length ? segments.join("") : null;
    }

    line.x = function (_) {
      if (!arguments.length) return x;
      x = _;
      return line;
    };

    line.y = function (_) {
      if (!arguments.length) return y;
      y = _;
      return line;
    };

    line.defined = function (_) {
      if (!arguments.length) return defined;
      defined = _;
      return line;
    };

    line.interpolate = function (_) {
      if (!arguments.length) return interpolateKey;
      if (typeof _ === "function") interpolateKey = interpolate = _;else interpolateKey = (interpolate = d3_svg_lineInterpolators.get(_) || d3_svg_lineLinear).key;
      return line;
    };

    line.tension = function (_) {
      if (!arguments.length) return tension;
      tension = _;
      return line;
    };

    return line;
  }

  d3.svg.line = function () {
    return d3_svg_line(d3_identity);
  };

  function d3_svg_lineX(d) {
    return d[0];
  }

  function d3_svg_lineY(d) {
    return d[1];
  }

  var d3_svg_lineInterpolators = d3.map({
    linear: d3_svg_lineLinear,
    "linear-closed": d3_svg_lineLinearClosed,
    "step-before": d3_svg_lineStepBefore,
    "step-after": d3_svg_lineStepAfter,
    basis: d3_svg_lineBasis,
    "basis-open": d3_svg_lineBasisOpen,
    "basis-closed": d3_svg_lineBasisClosed,
    bundle: d3_svg_lineBundle,
    cardinal: d3_svg_lineCardinal,
    "cardinal-open": d3_svg_lineCardinalOpen,
    "cardinal-closed": d3_svg_lineCardinalClosed,
    monotone: d3_svg_lineMonotone
  });
  d3_svg_lineInterpolators.forEach(function (key, value) {
    value.key = key;
    value.closed = /-closed$/.test(key);
  });

  function d3_svg_lineLinear(points) {
    return points.join("L");
  }

  function d3_svg_lineLinearClosed(points) {
    return d3_svg_lineLinear(points) + "Z";
  }

  function d3_svg_lineStepBefore(points) {
    var i = 0,
        n = points.length,
        p = points[0],
        path = [p[0], ",", p[1]];

    while (++i < n) {
      path.push("V", (p = points[i])[1], "H", p[0]);
    }

    return path.join("");
  }

  function d3_svg_lineStepAfter(points) {
    var i = 0,
        n = points.length,
        p = points[0],
        path = [p[0], ",", p[1]];

    while (++i < n) {
      path.push("H", (p = points[i])[0], "V", p[1]);
    }

    return path.join("");
  }

  function d3_svg_lineCardinalOpen(points, tension) {
    return points.length < 4 ? d3_svg_lineLinear(points) : points[1] + d3_svg_lineHermite(points.slice(1, points.length - 1), d3_svg_lineCardinalTangents(points, tension));
  }

  function d3_svg_lineCardinalClosed(points, tension) {
    return points.length < 3 ? d3_svg_lineLinear(points) : points[0] + d3_svg_lineHermite((points.push(points[0]), points), d3_svg_lineCardinalTangents([points[points.length - 2]].concat(points, [points[1]]), tension));
  }

  function d3_svg_lineCardinal(points, tension) {
    return points.length < 3 ? d3_svg_lineLinear(points) : points[0] + d3_svg_lineHermite(points, d3_svg_lineCardinalTangents(points, tension));
  }

  function d3_svg_lineHermite(points, tangents) {
    if (tangents.length < 1 || points.length != tangents.length && points.length != tangents.length + 2) {
      return d3_svg_lineLinear(points);
    }

    var quad = points.length != tangents.length,
        path = "",
        p0 = points[0],
        p = points[1],
        t0 = tangents[0],
        t = t0,
        pi = 1;

    if (quad) {
      path += "Q" + (p[0] - t0[0] * 2 / 3) + "," + (p[1] - t0[1] * 2 / 3) + "," + p[0] + "," + p[1];
      p0 = points[1];
      pi = 2;
    }

    if (tangents.length > 1) {
      t = tangents[1];
      p = points[pi];
      pi++;
      path += "C" + (p0[0] + t0[0]) + "," + (p0[1] + t0[1]) + "," + (p[0] - t[0]) + "," + (p[1] - t[1]) + "," + p[0] + "," + p[1];

      for (var i = 2; i < tangents.length; i++, pi++) {
        p = points[pi];
        t = tangents[i];
        path += "S" + (p[0] - t[0]) + "," + (p[1] - t[1]) + "," + p[0] + "," + p[1];
      }
    }

    if (quad) {
      var lp = points[pi];
      path += "Q" + (p[0] + t[0] * 2 / 3) + "," + (p[1] + t[1] * 2 / 3) + "," + lp[0] + "," + lp[1];
    }

    return path;
  }

  function d3_svg_lineCardinalTangents(points, tension) {
    var tangents = [],
        a = (1 - tension) / 2,
        p0,
        p1 = points[0],
        p2 = points[1],
        i = 1,
        n = points.length;

    while (++i < n) {
      p0 = p1;
      p1 = p2;
      p2 = points[i];
      tangents.push([a * (p2[0] - p0[0]), a * (p2[1] - p0[1])]);
    }

    return tangents;
  }

  function d3_svg_lineBasis(points) {
    if (points.length < 3) return d3_svg_lineLinear(points);
    var i = 1,
        n = points.length,
        pi = points[0],
        x0 = pi[0],
        y0 = pi[1],
        px = [x0, x0, x0, (pi = points[1])[0]],
        py = [y0, y0, y0, pi[1]],
        path = [x0, ",", y0];
    d3_svg_lineBasisBezier(path, px, py);

    while (++i < n) {
      pi = points[i];
      px.shift();
      px.push(pi[0]);
      py.shift();
      py.push(pi[1]);
      d3_svg_lineBasisBezier(path, px, py);
    }

    i = -1;

    while (++i < 2) {
      px.shift();
      px.push(pi[0]);
      py.shift();
      py.push(pi[1]);
      d3_svg_lineBasisBezier(path, px, py);
    }

    return path.join("");
  }

  function d3_svg_lineBasisOpen(points) {
    if (points.length < 4) return d3_svg_lineLinear(points);
    var path = [],
        i = -1,
        n = points.length,
        pi,
        px = [0],
        py = [0];

    while (++i < 3) {
      pi = points[i];
      px.push(pi[0]);
      py.push(pi[1]);
    }

    path.push(d3_svg_lineDot4(d3_svg_lineBasisBezier3, px) + "," + d3_svg_lineDot4(d3_svg_lineBasisBezier3, py));
    --i;

    while (++i < n) {
      pi = points[i];
      px.shift();
      px.push(pi[0]);
      py.shift();
      py.push(pi[1]);
      d3_svg_lineBasisBezier(path, px, py);
    }

    return path.join("");
  }

  function d3_svg_lineBasisClosed(points) {
    var path,
        i = -1,
        n = points.length,
        m = n + 4,
        pi,
        px = [],
        py = [];

    while (++i < 4) {
      pi = points[i % n];
      px.push(pi[0]);
      py.push(pi[1]);
    }

    path = [d3_svg_lineDot4(d3_svg_lineBasisBezier3, px), ",", d3_svg_lineDot4(d3_svg_lineBasisBezier3, py)];
    --i;

    while (++i < m) {
      pi = points[i % n];
      px.shift();
      px.push(pi[0]);
      py.shift();
      py.push(pi[1]);
      d3_svg_lineBasisBezier(path, px, py);
    }

    return path.join("");
  }

  function d3_svg_lineBundle(points, tension) {
    var n = points.length - 1;

    if (n) {
      var x0 = points[0][0],
          y0 = points[0][1],
          dx = points[n][0] - x0,
          dy = points[n][1] - y0,
          i = -1,
          p,
          t;

      while (++i <= n) {
        p = points[i];
        t = i / n;
        p[0] = tension * p[0] + (1 - tension) * (x0 + t * dx);
        p[1] = tension * p[1] + (1 - tension) * (y0 + t * dy);
      }
    }

    return d3_svg_lineBasis(points);
  }

  function d3_svg_lineDot4(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
  }

  var d3_svg_lineBasisBezier1 = [0, 2 / 3, 1 / 3, 0],
      d3_svg_lineBasisBezier2 = [0, 1 / 3, 2 / 3, 0],
      d3_svg_lineBasisBezier3 = [0, 1 / 6, 2 / 3, 1 / 6];

  function d3_svg_lineBasisBezier(path, x, y) {
    path.push("C", d3_svg_lineDot4(d3_svg_lineBasisBezier1, x), ",", d3_svg_lineDot4(d3_svg_lineBasisBezier1, y), ",", d3_svg_lineDot4(d3_svg_lineBasisBezier2, x), ",", d3_svg_lineDot4(d3_svg_lineBasisBezier2, y), ",", d3_svg_lineDot4(d3_svg_lineBasisBezier3, x), ",", d3_svg_lineDot4(d3_svg_lineBasisBezier3, y));
  }

  function d3_svg_lineSlope(p0, p1) {
    return (p1[1] - p0[1]) / (p1[0] - p0[0]);
  }

  function d3_svg_lineFiniteDifferences(points) {
    var i = 0,
        j = points.length - 1,
        m = [],
        p0 = points[0],
        p1 = points[1],
        d = m[0] = d3_svg_lineSlope(p0, p1);

    while (++i < j) {
      m[i] = (d + (d = d3_svg_lineSlope(p0 = p1, p1 = points[i + 1]))) / 2;
    }

    m[i] = d;
    return m;
  }

  function d3_svg_lineMonotoneTangents(points) {
    var tangents = [],
        d,
        a,
        b,
        s,
        m = d3_svg_lineFiniteDifferences(points),
        i = -1,
        j = points.length - 1;

    while (++i < j) {
      d = d3_svg_lineSlope(points[i], points[i + 1]);

      if (Math.abs(d) < 1e-6) {
        m[i] = m[i + 1] = 0;
      } else {
        a = m[i] / d;
        b = m[i + 1] / d;
        s = a * a + b * b;

        if (s > 9) {
          s = d * 3 / Math.sqrt(s);
          m[i] = s * a;
          m[i + 1] = s * b;
        }
      }
    }

    i = -1;

    while (++i <= j) {
      s = (points[Math.min(j, i + 1)][0] - points[Math.max(0, i - 1)][0]) / (6 * (1 + m[i] * m[i]));
      tangents.push([s || 0, m[i] * s || 0]);
    }

    return tangents;
  }

  function d3_svg_lineMonotone(points) {
    return points.length < 3 ? d3_svg_lineLinear(points) : points[0] + d3_svg_lineHermite(points, d3_svg_lineMonotoneTangents(points));
  }

  d3.geom.hull = function (vertices) {
    var x = d3_svg_lineX,
        y = d3_svg_lineY;
    if (arguments.length) return hull(vertices);

    function hull(data) {
      if (data.length < 3) return [];
      var fx = d3_functor(x),
          fy = d3_functor(y),
          n = data.length,
          vertices,
          plen = n - 1,
          points = [],
          stack = [],
          d,
          i,
          j,
          h = 0,
          x1,
          y1,
          x2,
          y2,
          u,
          v,
          a,
          sp;
      if (fx === d3_svg_lineX && y === d3_svg_lineY) vertices = data;else for (i = 0, vertices = []; i < n; ++i) {
        vertices.push([+fx.call(this, d = data[i], i), +fy.call(this, d, i)]);
      }

      for (i = 1; i < n; ++i) {
        if (vertices[i][1] < vertices[h][1]) {
          h = i;
        } else if (vertices[i][1] == vertices[h][1]) {
          h = vertices[i][0] < vertices[h][0] ? i : h;
        }
      }

      for (i = 0; i < n; ++i) {
        if (i === h) continue;
        y1 = vertices[i][1] - vertices[h][1];
        x1 = vertices[i][0] - vertices[h][0];
        points.push({
          angle: Math.atan2(y1, x1),
          index: i
        });
      }

      points.sort(function (a, b) {
        return a.angle - b.angle;
      });
      a = points[0].angle;
      v = points[0].index;
      u = 0;

      for (i = 1; i < plen; ++i) {
        j = points[i].index;

        if (a == points[i].angle) {
          x1 = vertices[v][0] - vertices[h][0];
          y1 = vertices[v][1] - vertices[h][1];
          x2 = vertices[j][0] - vertices[h][0];
          y2 = vertices[j][1] - vertices[h][1];

          if (x1 * x1 + y1 * y1 >= x2 * x2 + y2 * y2) {
            points[i].index = -1;
          } else {
            points[u].index = -1;
            a = points[i].angle;
            u = i;
            v = j;
          }
        } else {
          a = points[i].angle;
          u = i;
          v = j;
        }
      }

      stack.push(h);

      for (i = 0, j = 0; i < 2; ++j) {
        if (points[j].index !== -1) {
          stack.push(points[j].index);
          i++;
        }
      }

      sp = stack.length;

      for (; j < plen; ++j) {
        if (points[j].index === -1) continue;

        while (!d3_geom_hullCCW(stack[sp - 2], stack[sp - 1], points[j].index, vertices)) {
          --sp;
        }

        stack[sp++] = points[j].index;
      }

      var poly = [];

      for (i = 0; i < sp; ++i) {
        poly.push(data[stack[i]]);
      }

      return poly;
    }

    hull.x = function (_) {
      return arguments.length ? (x = _, hull) : x;
    };

    hull.y = function (_) {
      return arguments.length ? (y = _, hull) : y;
    };

    return hull;
  };

  function d3_geom_hullCCW(i1, i2, i3, v) {
    var t, a, b, c, d, e, f;
    t = v[i1];
    a = t[0];
    b = t[1];
    t = v[i2];
    c = t[0];
    d = t[1];
    t = v[i3];
    e = t[0];
    f = t[1];
    return (f - b) * (c - a) - (d - b) * (e - a) > 0;
  }

  d3.geom.polygon = function (coordinates) {
    coordinates.area = function () {
      var i = 0,
          n = coordinates.length,
          area = coordinates[n - 1][1] * coordinates[0][0] - coordinates[n - 1][0] * coordinates[0][1];

      while (++i < n) {
        area += coordinates[i - 1][1] * coordinates[i][0] - coordinates[i - 1][0] * coordinates[i][1];
      }

      return area * .5;
    };

    coordinates.centroid = function (k) {
      var i = -1,
          n = coordinates.length,
          x = 0,
          y = 0,
          a,
          b = coordinates[n - 1],
          c;
      if (!arguments.length) k = -1 / (6 * coordinates.area());

      while (++i < n) {
        a = b;
        b = coordinates[i];
        c = a[0] * b[1] - b[0] * a[1];
        x += (a[0] + b[0]) * c;
        y += (a[1] + b[1]) * c;
      }

      return [x * k, y * k];
    };

    coordinates.clip = function (subject) {
      var input,
          i = -1,
          n = coordinates.length,
          j,
          m,
          a = coordinates[n - 1],
          b,
          c,
          d;

      while (++i < n) {
        input = subject.slice();
        subject.length = 0;
        b = coordinates[i];
        c = input[(m = input.length) - 1];
        j = -1;

        while (++j < m) {
          d = input[j];

          if (d3_geom_polygonInside(d, a, b)) {
            if (!d3_geom_polygonInside(c, a, b)) {
              subject.push(d3_geom_polygonIntersect(c, d, a, b));
            }

            subject.push(d);
          } else if (d3_geom_polygonInside(c, a, b)) {
            subject.push(d3_geom_polygonIntersect(c, d, a, b));
          }

          c = d;
        }

        a = b;
      }

      return subject;
    };

    return coordinates;
  };

  function d3_geom_polygonInside(p, a, b) {
    return (b[0] - a[0]) * (p[1] - a[1]) < (b[1] - a[1]) * (p[0] - a[0]);
  }

  function d3_geom_polygonIntersect(c, d, a, b) {
    var x1 = c[0],
        x3 = a[0],
        x21 = d[0] - x1,
        x43 = b[0] - x3,
        y1 = c[1],
        y3 = a[1],
        y21 = d[1] - y1,
        y43 = b[1] - y3,
        ua = (x43 * (y1 - y3) - y43 * (x1 - x3)) / (y43 * x21 - x43 * y21);
    return [x1 + ua * x21, y1 + ua * y21];
  }

  d3.geom.delaunay = function (vertices) {
    var edges = vertices.map(function () {
      return [];
    }),
        triangles = [];
    d3_geom_voronoiTessellate(vertices, function (e) {
      edges[e.region.l.index].push(vertices[e.region.r.index]);
    });
    edges.forEach(function (edge, i) {
      var v = vertices[i],
          cx = v[0],
          cy = v[1];
      edge.forEach(function (v) {
        v.angle = Math.atan2(v[0] - cx, v[1] - cy);
      });
      edge.sort(function (a, b) {
        return a.angle - b.angle;
      });

      for (var j = 0, m = edge.length - 1; j < m; j++) {
        triangles.push([v, edge[j], edge[j + 1]]);
      }
    });
    return triangles;
  };

  d3.geom.voronoi = function (points) {
    var size = null,
        x = d3_svg_lineX,
        y = d3_svg_lineY,
        clip;
    if (arguments.length) return voronoi(points);

    function voronoi(data) {
      var points,
          polygons = data.map(function () {
        return [];
      }),
          fx = d3_functor(x),
          fy = d3_functor(y),
          d,
          i,
          n = data.length,
          Z = 1e6;
      if (fx === d3_svg_lineX && fy === d3_svg_lineY) points = data;else for (points = [], i = 0; i < n; ++i) {
        points.push([+fx.call(this, d = data[i], i), +fy.call(this, d, i)]);
      }
      d3_geom_voronoiTessellate(points, function (e) {
        var s1, s2, x1, x2, y1, y2;

        if (e.a === 1 && e.b >= 0) {
          s1 = e.ep.r;
          s2 = e.ep.l;
        } else {
          s1 = e.ep.l;
          s2 = e.ep.r;
        }

        if (e.a === 1) {
          y1 = s1 ? s1.y : -Z;
          x1 = e.c - e.b * y1;
          y2 = s2 ? s2.y : Z;
          x2 = e.c - e.b * y2;
        } else {
          x1 = s1 ? s1.x : -Z;
          y1 = e.c - e.a * x1;
          x2 = s2 ? s2.x : Z;
          y2 = e.c - e.a * x2;
        }

        var v1 = [x1, y1],
            v2 = [x2, y2];
        polygons[e.region.l.index].push(v1, v2);
        polygons[e.region.r.index].push(v1, v2);
      });
      polygons = polygons.map(function (polygon, i) {
        var cx = points[i][0],
            cy = points[i][1],
            angle = polygon.map(function (v) {
          return Math.atan2(v[0] - cx, v[1] - cy);
        }),
            order = d3.range(polygon.length).sort(function (a, b) {
          return angle[a] - angle[b];
        });
        return order.filter(function (d, i) {
          return !i || angle[d] - angle[order[i - 1]] > ε;
        }).map(function (d) {
          return polygon[d];
        });
      });
      polygons.forEach(function (polygon, i) {
        var n = polygon.length;
        if (!n) return polygon.push([-Z, -Z], [-Z, Z], [Z, Z], [Z, -Z]);
        if (n > 2) return;
        var p0 = points[i],
            p1 = polygon[0],
            p2 = polygon[1],
            x0 = p0[0],
            y0 = p0[1],
            x1 = p1[0],
            y1 = p1[1],
            x2 = p2[0],
            y2 = p2[1],
            dx = Math.abs(x2 - x1),
            dy = y2 - y1;

        if (Math.abs(dy) < ε) {
          var y = y0 < y1 ? -Z : Z;
          polygon.push([-Z, y], [Z, y]);
        } else if (dx < ε) {
          var x = x0 < x1 ? -Z : Z;
          polygon.push([x, -Z], [x, Z]);
        } else {
          var y = (x2 - x1) * (y1 - y0) < (x1 - x0) * (y2 - y1) ? Z : -Z,
              z = Math.abs(dy) - dx;

          if (Math.abs(z) < ε) {
            polygon.push([dy < 0 ? y : -y, y]);
          } else {
            if (z > 0) y *= -1;
            polygon.push([-Z, y], [Z, y]);
          }
        }
      });
      if (clip) for (i = 0; i < n; ++i) {
        clip(polygons[i]);
      }

      for (i = 0; i < n; ++i) {
        polygons[i].point = data[i];
      }

      return polygons;
    }

    voronoi.x = function (_) {
      return arguments.length ? (x = _, voronoi) : x;
    };

    voronoi.y = function (_) {
      return arguments.length ? (y = _, voronoi) : y;
    };

    voronoi.size = function (_) {
      if (!arguments.length) return size;

      if (_ == null) {
        clip = null;
      } else {
        size = [+_[0], +_[1]];
        clip = d3.geom.polygon([[0, 0], [0, size[1]], size, [size[0], 0]]).clip;
      }

      return voronoi;
    };

    voronoi.links = function (data) {
      var points,
          graph = data.map(function () {
        return [];
      }),
          links = [],
          fx = d3_functor(x),
          fy = d3_functor(y),
          d,
          i,
          n = data.length;
      if (fx === d3_svg_lineX && fy === d3_svg_lineY) points = data;else for (i = 0; i < n; ++i) {
        points.push([+fx.call(this, d = data[i], i), +fy.call(this, d, i)]);
      }
      d3_geom_voronoiTessellate(points, function (e) {
        var l = e.region.l.index,
            r = e.region.r.index;
        if (graph[l][r]) return;
        graph[l][r] = graph[r][l] = true;
        links.push({
          source: data[l],
          target: data[r]
        });
      });
      return links;
    };

    voronoi.triangles = function (data) {
      if (x === d3_svg_lineX && y === d3_svg_lineY) return d3.geom.delaunay(data);
      var points,
          point,
          fx = d3_functor(x),
          fy = d3_functor(y),
          d,
          i,
          n;

      for (i = 0, points = [], n = data.length; i < n; ++i) {
        point = [+fx.call(this, d = data[i], i), +fy.call(this, d, i)];
        point.data = d;
        points.push(point);
      }

      return d3.geom.delaunay(points).map(function (triangle) {
        return triangle.map(function (point) {
          return point.data;
        });
      });
    };

    return voronoi;
  };

  var d3_geom_voronoiOpposite = {
    l: "r",
    r: "l"
  };

  function d3_geom_voronoiTessellate(points, callback) {
    var Sites = {
      list: points.map(function (v, i) {
        return {
          index: i,
          x: v[0],
          y: v[1]
        };
      }).sort(function (a, b) {
        return a.y < b.y ? -1 : a.y > b.y ? 1 : a.x < b.x ? -1 : a.x > b.x ? 1 : 0;
      }),
      bottomSite: null
    };
    var EdgeList = {
      list: [],
      leftEnd: null,
      rightEnd: null,
      init: function init() {
        EdgeList.leftEnd = EdgeList.createHalfEdge(null, "l");
        EdgeList.rightEnd = EdgeList.createHalfEdge(null, "l");
        EdgeList.leftEnd.r = EdgeList.rightEnd;
        EdgeList.rightEnd.l = EdgeList.leftEnd;
        EdgeList.list.unshift(EdgeList.leftEnd, EdgeList.rightEnd);
      },
      createHalfEdge: function createHalfEdge(edge, side) {
        return {
          edge: edge,
          side: side,
          vertex: null,
          l: null,
          r: null
        };
      },
      insert: function insert(lb, he) {
        he.l = lb;
        he.r = lb.r;
        lb.r.l = he;
        lb.r = he;
      },
      leftBound: function leftBound(p) {
        var he = EdgeList.leftEnd;

        do {
          he = he.r;
        } while (he != EdgeList.rightEnd && Geom.rightOf(he, p));

        he = he.l;
        return he;
      },
      del: function del(he) {
        he.l.r = he.r;
        he.r.l = he.l;
        he.edge = null;
      },
      right: function right(he) {
        return he.r;
      },
      left: function left(he) {
        return he.l;
      },
      leftRegion: function leftRegion(he) {
        return he.edge == null ? Sites.bottomSite : he.edge.region[he.side];
      },
      rightRegion: function rightRegion(he) {
        return he.edge == null ? Sites.bottomSite : he.edge.region[d3_geom_voronoiOpposite[he.side]];
      }
    };
    var Geom = {
      bisect: function bisect(s1, s2) {
        var newEdge = {
          region: {
            l: s1,
            r: s2
          },
          ep: {
            l: null,
            r: null
          }
        };
        var dx = s2.x - s1.x,
            dy = s2.y - s1.y,
            adx = dx > 0 ? dx : -dx,
            ady = dy > 0 ? dy : -dy;
        newEdge.c = s1.x * dx + s1.y * dy + (dx * dx + dy * dy) * .5;

        if (adx > ady) {
          newEdge.a = 1;
          newEdge.b = dy / dx;
          newEdge.c /= dx;
        } else {
          newEdge.b = 1;
          newEdge.a = dx / dy;
          newEdge.c /= dy;
        }

        return newEdge;
      },
      intersect: function intersect(el1, el2) {
        var e1 = el1.edge,
            e2 = el2.edge;

        if (!e1 || !e2 || e1.region.r == e2.region.r) {
          return null;
        }

        var d = e1.a * e2.b - e1.b * e2.a;

        if (Math.abs(d) < 1e-10) {
          return null;
        }

        var xint = (e1.c * e2.b - e2.c * e1.b) / d,
            yint = (e2.c * e1.a - e1.c * e2.a) / d,
            e1r = e1.region.r,
            e2r = e2.region.r,
            el,
            e;

        if (e1r.y < e2r.y || e1r.y == e2r.y && e1r.x < e2r.x) {
          el = el1;
          e = e1;
        } else {
          el = el2;
          e = e2;
        }

        var rightOfSite = xint >= e.region.r.x;

        if (rightOfSite && el.side === "l" || !rightOfSite && el.side === "r") {
          return null;
        }

        return {
          x: xint,
          y: yint
        };
      },
      rightOf: function rightOf(he, p) {
        var e = he.edge,
            topsite = e.region.r,
            rightOfSite = p.x > topsite.x;

        if (rightOfSite && he.side === "l") {
          return 1;
        }

        if (!rightOfSite && he.side === "r") {
          return 0;
        }

        if (e.a === 1) {
          var dyp = p.y - topsite.y,
              dxp = p.x - topsite.x,
              fast = 0,
              above = 0;

          if (!rightOfSite && e.b < 0 || rightOfSite && e.b >= 0) {
            above = fast = dyp >= e.b * dxp;
          } else {
            above = p.x + p.y * e.b > e.c;

            if (e.b < 0) {
              above = !above;
            }

            if (!above) {
              fast = 1;
            }
          }

          if (!fast) {
            var dxs = topsite.x - e.region.l.x;
            above = e.b * (dxp * dxp - dyp * dyp) < dxs * dyp * (1 + 2 * dxp / dxs + e.b * e.b);

            if (e.b < 0) {
              above = !above;
            }
          }
        } else {
          var yl = e.c - e.a * p.x,
              t1 = p.y - yl,
              t2 = p.x - topsite.x,
              t3 = yl - topsite.y;
          above = t1 * t1 > t2 * t2 + t3 * t3;
        }

        return he.side === "l" ? above : !above;
      },
      endPoint: function endPoint(edge, side, site) {
        edge.ep[side] = site;
        if (!edge.ep[d3_geom_voronoiOpposite[side]]) return;
        callback(edge);
      },
      distance: function distance(s, t) {
        var dx = s.x - t.x,
            dy = s.y - t.y;
        return Math.sqrt(dx * dx + dy * dy);
      }
    };
    var EventQueue = {
      list: [],
      insert: function insert(he, site, offset) {
        he.vertex = site;
        he.ystar = site.y + offset;

        for (var i = 0, list = EventQueue.list, l = list.length; i < l; i++) {
          var next = list[i];

          if (he.ystar > next.ystar || he.ystar == next.ystar && site.x > next.vertex.x) {
            continue;
          } else {
            break;
          }
        }

        list.splice(i, 0, he);
      },
      del: function del(he) {
        for (var i = 0, ls = EventQueue.list, l = ls.length; i < l && ls[i] != he; ++i) {}

        ls.splice(i, 1);
      },
      empty: function empty() {
        return EventQueue.list.length === 0;
      },
      nextEvent: function nextEvent(he) {
        for (var i = 0, ls = EventQueue.list, l = ls.length; i < l; ++i) {
          if (ls[i] == he) return ls[i + 1];
        }

        return null;
      },
      min: function min() {
        var elem = EventQueue.list[0];
        return {
          x: elem.vertex.x,
          y: elem.ystar
        };
      },
      extractMin: function extractMin() {
        return EventQueue.list.shift();
      }
    };
    EdgeList.init();
    Sites.bottomSite = Sites.list.shift();
    var newSite = Sites.list.shift(),
        newIntStar;
    var lbnd, rbnd, llbnd, rrbnd, bisector;
    var bot, top, temp, p, v;
    var e, pm;

    while (true) {
      if (!EventQueue.empty()) {
        newIntStar = EventQueue.min();
      }

      if (newSite && (EventQueue.empty() || newSite.y < newIntStar.y || newSite.y == newIntStar.y && newSite.x < newIntStar.x)) {
        lbnd = EdgeList.leftBound(newSite);
        rbnd = EdgeList.right(lbnd);
        bot = EdgeList.rightRegion(lbnd);
        e = Geom.bisect(bot, newSite);
        bisector = EdgeList.createHalfEdge(e, "l");
        EdgeList.insert(lbnd, bisector);
        p = Geom.intersect(lbnd, bisector);

        if (p) {
          EventQueue.del(lbnd);
          EventQueue.insert(lbnd, p, Geom.distance(p, newSite));
        }

        lbnd = bisector;
        bisector = EdgeList.createHalfEdge(e, "r");
        EdgeList.insert(lbnd, bisector);
        p = Geom.intersect(bisector, rbnd);

        if (p) {
          EventQueue.insert(bisector, p, Geom.distance(p, newSite));
        }

        newSite = Sites.list.shift();
      } else if (!EventQueue.empty()) {
        lbnd = EventQueue.extractMin();
        llbnd = EdgeList.left(lbnd);
        rbnd = EdgeList.right(lbnd);
        rrbnd = EdgeList.right(rbnd);
        bot = EdgeList.leftRegion(lbnd);
        top = EdgeList.rightRegion(rbnd);
        v = lbnd.vertex;
        Geom.endPoint(lbnd.edge, lbnd.side, v);
        Geom.endPoint(rbnd.edge, rbnd.side, v);
        EdgeList.del(lbnd);
        EventQueue.del(rbnd);
        EdgeList.del(rbnd);
        pm = "l";

        if (bot.y > top.y) {
          temp = bot;
          bot = top;
          top = temp;
          pm = "r";
        }

        e = Geom.bisect(bot, top);
        bisector = EdgeList.createHalfEdge(e, pm);
        EdgeList.insert(llbnd, bisector);
        Geom.endPoint(e, d3_geom_voronoiOpposite[pm], v);
        p = Geom.intersect(llbnd, bisector);

        if (p) {
          EventQueue.del(llbnd);
          EventQueue.insert(llbnd, p, Geom.distance(p, bot));
        }

        p = Geom.intersect(bisector, rrbnd);

        if (p) {
          EventQueue.insert(bisector, p, Geom.distance(p, bot));
        }
      } else {
        break;
      }
    }

    for (lbnd = EdgeList.right(EdgeList.leftEnd); lbnd != EdgeList.rightEnd; lbnd = EdgeList.right(lbnd)) {
      callback(lbnd.edge);
    }
  }

  d3.geom.quadtree = function (points, x1, y1, x2, y2) {
    var x = d3_svg_lineX,
        y = d3_svg_lineY,
        compat;

    if (compat = arguments.length) {
      x = d3_geom_quadtreeCompatX;
      y = d3_geom_quadtreeCompatY;

      if (compat === 3) {
        y2 = y1;
        x2 = x1;
        y1 = x1 = 0;
      }

      return quadtree(points);
    }

    function quadtree(data) {
      var d,
          fx = d3_functor(x),
          fy = d3_functor(y),
          xs,
          ys,
          i,
          n,
          x1_,
          y1_,
          x2_,
          y2_;

      if (x1 != null) {
        x1_ = x1, y1_ = y1, x2_ = x2, y2_ = y2;
      } else {
        x2_ = y2_ = -(x1_ = y1_ = Infinity);
        xs = [], ys = [];
        n = data.length;
        if (compat) for (i = 0; i < n; ++i) {
          d = data[i];
          if (d.x < x1_) x1_ = d.x;
          if (d.y < y1_) y1_ = d.y;
          if (d.x > x2_) x2_ = d.x;
          if (d.y > y2_) y2_ = d.y;
          xs.push(d.x);
          ys.push(d.y);
        } else for (i = 0; i < n; ++i) {
          var x_ = +fx(d = data[i], i),
              y_ = +fy(d, i);
          if (x_ < x1_) x1_ = x_;
          if (y_ < y1_) y1_ = y_;
          if (x_ > x2_) x2_ = x_;
          if (y_ > y2_) y2_ = y_;
          xs.push(x_);
          ys.push(y_);
        }
      }

      var dx = x2_ - x1_,
          dy = y2_ - y1_;
      if (dx > dy) y2_ = y1_ + dx;else x2_ = x1_ + dy;

      function insert(n, d, x, y, x1, y1, x2, y2) {
        if (isNaN(x) || isNaN(y)) return;

        if (n.leaf) {
          var nx = n.x,
              ny = n.y;

          if (nx != null) {
            if (Math.abs(nx - x) + Math.abs(ny - y) < .01) {
              insertChild(n, d, x, y, x1, y1, x2, y2);
            } else {
              var nPoint = n.point;
              n.x = n.y = n.point = null;
              insertChild(n, nPoint, nx, ny, x1, y1, x2, y2);
              insertChild(n, d, x, y, x1, y1, x2, y2);
            }
          } else {
            n.x = x, n.y = y, n.point = d;
          }
        } else {
          insertChild(n, d, x, y, x1, y1, x2, y2);
        }
      }

      function insertChild(n, d, x, y, x1, y1, x2, y2) {
        var sx = (x1 + x2) * .5,
            sy = (y1 + y2) * .5,
            right = x >= sx,
            bottom = y >= sy,
            i = (bottom << 1) + right;
        n.leaf = false;
        n = n.nodes[i] || (n.nodes[i] = d3_geom_quadtreeNode());
        if (right) x1 = sx;else x2 = sx;
        if (bottom) y1 = sy;else y2 = sy;
        insert(n, d, x, y, x1, y1, x2, y2);
      }

      var root = d3_geom_quadtreeNode();

      root.add = function (d) {
        insert(root, d, +fx(d, ++i), +fy(d, i), x1_, y1_, x2_, y2_);
      };

      root.visit = function (f) {
        d3_geom_quadtreeVisit(f, root, x1_, y1_, x2_, y2_);
      };

      i = -1;

      if (x1 == null) {
        while (++i < n) {
          insert(root, data[i], xs[i], ys[i], x1_, y1_, x2_, y2_);
        }

        --i;
      } else data.forEach(root.add);

      xs = ys = data = d = null;
      return root;
    }

    quadtree.x = function (_) {
      return arguments.length ? (x = _, quadtree) : x;
    };

    quadtree.y = function (_) {
      return arguments.length ? (y = _, quadtree) : y;
    };

    quadtree.size = function (_) {
      if (!arguments.length) return x1 == null ? null : [x2, y2];

      if (_ == null) {
        x1 = y1 = x2 = y2 = null;
      } else {
        x1 = y1 = 0;
        x2 = +_[0], y2 = +_[1];
      }

      return quadtree;
    };

    return quadtree;
  };

  function d3_geom_quadtreeCompatX(d) {
    return d.x;
  }

  function d3_geom_quadtreeCompatY(d) {
    return d.y;
  }

  function d3_geom_quadtreeNode() {
    return {
      leaf: true,
      nodes: [],
      point: null,
      x: null,
      y: null
    };
  }

  function d3_geom_quadtreeVisit(f, node, x1, y1, x2, y2) {
    if (!f(node, x1, y1, x2, y2)) {
      var sx = (x1 + x2) * .5,
          sy = (y1 + y2) * .5,
          children = node.nodes;
      if (children[0]) d3_geom_quadtreeVisit(f, children[0], x1, y1, sx, sy);
      if (children[1]) d3_geom_quadtreeVisit(f, children[1], sx, y1, x2, sy);
      if (children[2]) d3_geom_quadtreeVisit(f, children[2], x1, sy, sx, y2);
      if (children[3]) d3_geom_quadtreeVisit(f, children[3], sx, sy, x2, y2);
    }
  }

  d3.interpolateRgb = d3_interpolateRgb;

  function d3_interpolateRgb(a, b) {
    a = d3.rgb(a);
    b = d3.rgb(b);
    var ar = a.r,
        ag = a.g,
        ab = a.b,
        br = b.r - ar,
        bg = b.g - ag,
        bb = b.b - ab;
    return function (t) {
      return "#" + d3_rgb_hex(Math.round(ar + br * t)) + d3_rgb_hex(Math.round(ag + bg * t)) + d3_rgb_hex(Math.round(ab + bb * t));
    };
  }

  d3.transform = function (string) {
    var g = d3_document.createElementNS(d3.ns.prefix.svg, "g");
    return (d3.transform = function (string) {
      g.setAttribute("transform", string);
      var t = g.transform.baseVal.consolidate();
      return new d3_transform(t ? t.matrix : d3_transformIdentity);
    })(string);
  };

  function d3_transform(m) {
    var r0 = [m.a, m.b],
        r1 = [m.c, m.d],
        kx = d3_transformNormalize(r0),
        kz = d3_transformDot(r0, r1),
        ky = d3_transformNormalize(d3_transformCombine(r1, r0, -kz)) || 0;

    if (r0[0] * r1[1] < r1[0] * r0[1]) {
      r0[0] *= -1;
      r0[1] *= -1;
      kx *= -1;
      kz *= -1;
    }

    this.rotate = (kx ? Math.atan2(r0[1], r0[0]) : Math.atan2(-r1[0], r1[1])) * d3_degrees;
    this.translate = [m.e, m.f];
    this.scale = [kx, ky];
    this.skew = ky ? Math.atan2(kz, ky) * d3_degrees : 0;
  }

  d3_transform.prototype.toString = function () {
    return "translate(" + this.translate + ")rotate(" + this.rotate + ")skewX(" + this.skew + ")scale(" + this.scale + ")";
  };

  function d3_transformDot(a, b) {
    return a[0] * b[0] + a[1] * b[1];
  }

  function d3_transformNormalize(a) {
    var k = Math.sqrt(d3_transformDot(a, a));

    if (k) {
      a[0] /= k;
      a[1] /= k;
    }

    return k;
  }

  function d3_transformCombine(a, b, k) {
    a[0] += k * b[0];
    a[1] += k * b[1];
    return a;
  }

  var d3_transformIdentity = {
    a: 1,
    b: 0,
    c: 0,
    d: 1,
    e: 0,
    f: 0
  };
  d3.interpolateNumber = d3_interpolateNumber;

  function d3_interpolateNumber(a, b) {
    b -= a;
    return function (t) {
      return a + b * t;
    };
  }

  d3.interpolateTransform = d3_interpolateTransform;

  function d3_interpolateTransform(a, b) {
    var s = [],
        q = [],
        n,
        A = d3.transform(a),
        B = d3.transform(b),
        ta = A.translate,
        tb = B.translate,
        ra = A.rotate,
        rb = B.rotate,
        wa = A.skew,
        wb = B.skew,
        ka = A.scale,
        kb = B.scale;

    if (ta[0] != tb[0] || ta[1] != tb[1]) {
      s.push("translate(", null, ",", null, ")");
      q.push({
        i: 1,
        x: d3_interpolateNumber(ta[0], tb[0])
      }, {
        i: 3,
        x: d3_interpolateNumber(ta[1], tb[1])
      });
    } else if (tb[0] || tb[1]) {
      s.push("translate(" + tb + ")");
    } else {
      s.push("");
    }

    if (ra != rb) {
      if (ra - rb > 180) rb += 360;else if (rb - ra > 180) ra += 360;
      q.push({
        i: s.push(s.pop() + "rotate(", null, ")") - 2,
        x: d3_interpolateNumber(ra, rb)
      });
    } else if (rb) {
      s.push(s.pop() + "rotate(" + rb + ")");
    }

    if (wa != wb) {
      q.push({
        i: s.push(s.pop() + "skewX(", null, ")") - 2,
        x: d3_interpolateNumber(wa, wb)
      });
    } else if (wb) {
      s.push(s.pop() + "skewX(" + wb + ")");
    }

    if (ka[0] != kb[0] || ka[1] != kb[1]) {
      n = s.push(s.pop() + "scale(", null, ",", null, ")");
      q.push({
        i: n - 4,
        x: d3_interpolateNumber(ka[0], kb[0])
      }, {
        i: n - 2,
        x: d3_interpolateNumber(ka[1], kb[1])
      });
    } else if (kb[0] != 1 || kb[1] != 1) {
      s.push(s.pop() + "scale(" + kb + ")");
    }

    n = q.length;
    return function (t) {
      var i = -1,
          o;

      while (++i < n) {
        s[(o = q[i]).i] = o.x(t);
      }

      return s.join("");
    };
  }

  d3.interpolateObject = d3_interpolateObject;

  function d3_interpolateObject(a, b) {
    var i = {},
        c = {},
        k;

    for (k in a) {
      if (k in b) {
        i[k] = d3_interpolateByName(k)(a[k], b[k]);
      } else {
        c[k] = a[k];
      }
    }

    for (k in b) {
      if (!(k in a)) {
        c[k] = b[k];
      }
    }

    return function (t) {
      for (k in i) {
        c[k] = i[k](t);
      }

      return c;
    };
  }

  d3.interpolateString = d3_interpolateString;

  function d3_interpolateString(a, b) {
    var m,
        i,
        j,
        s0 = 0,
        s1 = 0,
        s = [],
        q = [],
        n,
        o;
    d3_interpolate_number.lastIndex = 0;

    for (i = 0; m = d3_interpolate_number.exec(b); ++i) {
      if (m.index) s.push(b.substring(s0, s1 = m.index));
      q.push({
        i: s.length,
        x: m[0]
      });
      s.push(null);
      s0 = d3_interpolate_number.lastIndex;
    }

    if (s0 < b.length) s.push(b.substring(s0));

    for (i = 0, n = q.length; (m = d3_interpolate_number.exec(a)) && i < n; ++i) {
      o = q[i];

      if (o.x == m[0]) {
        if (o.i) {
          if (s[o.i + 1] == null) {
            s[o.i - 1] += o.x;
            s.splice(o.i, 1);

            for (j = i + 1; j < n; ++j) {
              q[j].i--;
            }
          } else {
            s[o.i - 1] += o.x + s[o.i + 1];
            s.splice(o.i, 2);

            for (j = i + 1; j < n; ++j) {
              q[j].i -= 2;
            }
          }
        } else {
          if (s[o.i + 1] == null) {
            s[o.i] = o.x;
          } else {
            s[o.i] = o.x + s[o.i + 1];
            s.splice(o.i + 1, 1);

            for (j = i + 1; j < n; ++j) {
              q[j].i--;
            }
          }
        }

        q.splice(i, 1);
        n--;
        i--;
      } else {
        o.x = d3_interpolateNumber(parseFloat(m[0]), parseFloat(o.x));
      }
    }

    while (i < n) {
      o = q.pop();

      if (s[o.i + 1] == null) {
        s[o.i] = o.x;
      } else {
        s[o.i] = o.x + s[o.i + 1];
        s.splice(o.i + 1, 1);
      }

      n--;
    }

    if (s.length === 1) {
      return s[0] == null ? q[0].x : function () {
        return b;
      };
    }

    return function (t) {
      for (i = 0; i < n; ++i) {
        s[(o = q[i]).i] = o.x(t);
      }

      return s.join("");
    };
  }

  var d3_interpolate_number = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g;
  d3.interpolate = d3_interpolate;

  function d3_interpolate(a, b) {
    var i = d3.interpolators.length,
        f;

    while (--i >= 0 && !(f = d3.interpolators[i](a, b))) {
      ;
    }

    return f;
  }

  function d3_interpolateByName(name) {
    return name == "transform" ? d3_interpolateTransform : d3_interpolate;
  }

  d3.interpolators = [d3_interpolateObject, function (a, b) {
    return Array.isArray(b) && d3_interpolateArray(a, b);
  }, function (a, b) {
    return (typeof a === "string" || typeof b === "string") && d3_interpolateString(a + "", b + "");
  }, function (a, b) {
    return (typeof b === "string" ? d3_rgb_names.has(b) || /^(#|rgb\(|hsl\()/.test(b) : b instanceof d3_Color) && d3_interpolateRgb(a, b);
  }, function (a, b) {
    return !isNaN(a = +a) && !isNaN(b = +b) && d3_interpolateNumber(a, b);
  }];
  d3.interpolateArray = d3_interpolateArray;

  function d3_interpolateArray(a, b) {
    var x = [],
        c = [],
        na = a.length,
        nb = b.length,
        n0 = Math.min(a.length, b.length),
        i;

    for (i = 0; i < n0; ++i) {
      x.push(d3_interpolate(a[i], b[i]));
    }

    for (; i < na; ++i) {
      c[i] = a[i];
    }

    for (; i < nb; ++i) {
      c[i] = b[i];
    }

    return function (t) {
      for (i = 0; i < n0; ++i) {
        c[i] = x[i](t);
      }

      return c;
    };
  }

  var d3_ease_default = function d3_ease_default() {
    return d3_identity;
  };

  var d3_ease = d3.map({
    linear: d3_ease_default,
    poly: d3_ease_poly,
    quad: function quad() {
      return d3_ease_quad;
    },
    cubic: function cubic() {
      return d3_ease_cubic;
    },
    sin: function sin() {
      return d3_ease_sin;
    },
    exp: function exp() {
      return d3_ease_exp;
    },
    circle: function circle() {
      return d3_ease_circle;
    },
    elastic: d3_ease_elastic,
    back: d3_ease_back,
    bounce: function bounce() {
      return d3_ease_bounce;
    }
  });
  var d3_ease_mode = d3.map({
    "in": d3_identity,
    out: d3_ease_reverse,
    "in-out": d3_ease_reflect,
    "out-in": function outIn(f) {
      return d3_ease_reflect(d3_ease_reverse(f));
    }
  });

  d3.ease = function (name) {
    var i = name.indexOf("-"),
        t = i >= 0 ? name.substring(0, i) : name,
        m = i >= 0 ? name.substring(i + 1) : "in";
    t = d3_ease.get(t) || d3_ease_default;
    m = d3_ease_mode.get(m) || d3_identity;
    return d3_ease_clamp(m(t.apply(null, Array.prototype.slice.call(arguments, 1))));
  };

  function d3_ease_clamp(f) {
    return function (t) {
      return t <= 0 ? 0 : t >= 1 ? 1 : f(t);
    };
  }

  function d3_ease_reverse(f) {
    return function (t) {
      return 1 - f(1 - t);
    };
  }

  function d3_ease_reflect(f) {
    return function (t) {
      return .5 * (t < .5 ? f(2 * t) : 2 - f(2 - 2 * t));
    };
  }

  function d3_ease_quad(t) {
    return t * t;
  }

  function d3_ease_cubic(t) {
    return t * t * t;
  }

  function d3_ease_cubicInOut(t) {
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    var t2 = t * t,
        t3 = t2 * t;
    return 4 * (t < .5 ? t3 : 3 * (t - t2) + t3 - .75);
  }

  function d3_ease_poly(e) {
    return function (t) {
      return Math.pow(t, e);
    };
  }

  function d3_ease_sin(t) {
    return 1 - Math.cos(t * π / 2);
  }

  function d3_ease_exp(t) {
    return Math.pow(2, 10 * (t - 1));
  }

  function d3_ease_circle(t) {
    return 1 - Math.sqrt(1 - t * t);
  }

  function d3_ease_elastic(a, p) {
    var s;
    if (arguments.length < 2) p = .45;
    if (arguments.length) s = p / (2 * π) * Math.asin(1 / a);else a = 1, s = p / 4;
    return function (t) {
      return 1 + a * Math.pow(2, 10 * -t) * Math.sin((t - s) * 2 * π / p);
    };
  }

  function d3_ease_back(s) {
    if (!s) s = 1.70158;
    return function (t) {
      return t * t * ((s + 1) * t - s);
    };
  }

  function d3_ease_bounce(t) {
    return t < 1 / 2.75 ? 7.5625 * t * t : t < 2 / 2.75 ? 7.5625 * (t -= 1.5 / 2.75) * t + .75 : t < 2.5 / 2.75 ? 7.5625 * (t -= 2.25 / 2.75) * t + .9375 : 7.5625 * (t -= 2.625 / 2.75) * t + .984375;
  }

  d3.interpolateHcl = d3_interpolateHcl;

  function d3_interpolateHcl(a, b) {
    a = d3.hcl(a);
    b = d3.hcl(b);
    var ah = a.h,
        ac = a.c,
        al = a.l,
        bh = b.h - ah,
        bc = b.c - ac,
        bl = b.l - al;
    if (bh > 180) bh -= 360;else if (bh < -180) bh += 360;
    return function (t) {
      return d3_hcl_lab(ah + bh * t, ac + bc * t, al + bl * t) + "";
    };
  }

  d3.interpolateHsl = d3_interpolateHsl;

  function d3_interpolateHsl(a, b) {
    a = d3.hsl(a);
    b = d3.hsl(b);
    var h0 = a.h,
        s0 = a.s,
        l0 = a.l,
        h1 = b.h - h0,
        s1 = b.s - s0,
        l1 = b.l - l0;
    if (h1 > 180) h1 -= 360;else if (h1 < -180) h1 += 360;
    return function (t) {
      return d3_hsl_rgb(h0 + h1 * t, s0 + s1 * t, l0 + l1 * t) + "";
    };
  }

  d3.interpolateLab = d3_interpolateLab;

  function d3_interpolateLab(a, b) {
    a = d3.lab(a);
    b = d3.lab(b);
    var al = a.l,
        aa = a.a,
        ab = a.b,
        bl = b.l - al,
        ba = b.a - aa,
        bb = b.b - ab;
    return function (t) {
      return d3_lab_rgb(al + bl * t, aa + ba * t, ab + bb * t) + "";
    };
  }

  d3.interpolateRound = d3_interpolateRound;

  function d3_interpolateRound(a, b) {
    b -= a;
    return function (t) {
      return Math.round(a + b * t);
    };
  }

  function d3_uninterpolateNumber(a, b) {
    b = b - (a = +a) ? 1 / (b - a) : 0;
    return function (x) {
      return (x - a) * b;
    };
  }

  function d3_uninterpolateClamp(a, b) {
    b = b - (a = +a) ? 1 / (b - a) : 0;
    return function (x) {
      return Math.max(0, Math.min(1, (x - a) * b));
    };
  }

  d3.layout = {};

  d3.layout.bundle = function () {
    return function (links) {
      var paths = [],
          i = -1,
          n = links.length;

      while (++i < n) {
        paths.push(d3_layout_bundlePath(links[i]));
      }

      return paths;
    };
  };

  function d3_layout_bundlePath(link) {
    var start = link.source,
        end = link.target,
        lca = d3_layout_bundleLeastCommonAncestor(start, end),
        points = [start];

    while (start !== lca) {
      start = start.parent;
      points.push(start);
    }

    var k = points.length;

    while (end !== lca) {
      points.splice(k, 0, end);
      end = end.parent;
    }

    return points;
  }

  function d3_layout_bundleAncestors(node) {
    var ancestors = [],
        parent = node.parent;

    while (parent != null) {
      ancestors.push(node);
      node = parent;
      parent = parent.parent;
    }

    ancestors.push(node);
    return ancestors;
  }

  function d3_layout_bundleLeastCommonAncestor(a, b) {
    if (a === b) return a;
    var aNodes = d3_layout_bundleAncestors(a),
        bNodes = d3_layout_bundleAncestors(b),
        aNode = aNodes.pop(),
        bNode = bNodes.pop(),
        sharedNode = null;

    while (aNode === bNode) {
      sharedNode = aNode;
      aNode = aNodes.pop();
      bNode = bNodes.pop();
    }

    return sharedNode;
  }

  d3.layout.chord = function () {
    var chord = {},
        chords,
        groups,
        matrix,
        n,
        padding = 0,
        sortGroups,
        sortSubgroups,
        sortChords;

    function relayout() {
      var subgroups = {},
          groupSums = [],
          groupIndex = d3.range(n),
          subgroupIndex = [],
          k,
          x,
          x0,
          i,
          j;
      chords = [];
      groups = [];
      k = 0, i = -1;

      while (++i < n) {
        x = 0, j = -1;

        while (++j < n) {
          x += matrix[i][j];
        }

        groupSums.push(x);
        subgroupIndex.push(d3.range(n));
        k += x;
      }

      if (sortGroups) {
        groupIndex.sort(function (a, b) {
          return sortGroups(groupSums[a], groupSums[b]);
        });
      }

      if (sortSubgroups) {
        subgroupIndex.forEach(function (d, i) {
          d.sort(function (a, b) {
            return sortSubgroups(matrix[i][a], matrix[i][b]);
          });
        });
      }

      k = (2 * π - padding * n) / k;
      x = 0, i = -1;

      while (++i < n) {
        x0 = x, j = -1;

        while (++j < n) {
          var di = groupIndex[i],
              dj = subgroupIndex[di][j],
              v = matrix[di][dj],
              a0 = x,
              a1 = x += v * k;
          subgroups[di + "-" + dj] = {
            index: di,
            subindex: dj,
            startAngle: a0,
            endAngle: a1,
            value: v
          };
        }

        groups[di] = {
          index: di,
          startAngle: x0,
          endAngle: x,
          value: (x - x0) / k
        };
        x += padding;
      }

      i = -1;

      while (++i < n) {
        j = i - 1;

        while (++j < n) {
          var source = subgroups[i + "-" + j],
              target = subgroups[j + "-" + i];

          if (source.value || target.value) {
            chords.push(source.value < target.value ? {
              source: target,
              target: source
            } : {
              source: source,
              target: target
            });
          }
        }
      }

      if (sortChords) resort();
    }

    function resort() {
      chords.sort(function (a, b) {
        return sortChords((a.source.value + a.target.value) / 2, (b.source.value + b.target.value) / 2);
      });
    }

    chord.matrix = function (x) {
      if (!arguments.length) return matrix;
      n = (matrix = x) && matrix.length;
      chords = groups = null;
      return chord;
    };

    chord.padding = function (x) {
      if (!arguments.length) return padding;
      padding = x;
      chords = groups = null;
      return chord;
    };

    chord.sortGroups = function (x) {
      if (!arguments.length) return sortGroups;
      sortGroups = x;
      chords = groups = null;
      return chord;
    };

    chord.sortSubgroups = function (x) {
      if (!arguments.length) return sortSubgroups;
      sortSubgroups = x;
      chords = null;
      return chord;
    };

    chord.sortChords = function (x) {
      if (!arguments.length) return sortChords;
      sortChords = x;
      if (chords) resort();
      return chord;
    };

    chord.chords = function () {
      if (!chords) relayout();
      return chords;
    };

    chord.groups = function () {
      if (!groups) relayout();
      return groups;
    };

    return chord;
  };

  d3.layout.force = function () {
    var force = {},
        event = d3.dispatch("start", "tick", "end"),
        size = [1, 1],
        drag,
        alpha,
        friction = .9,
        linkDistance = d3_layout_forceLinkDistance,
        linkStrength = d3_layout_forceLinkStrength,
        charge = -30,
        gravity = .1,
        theta = .8,
        nodes = [],
        links = [],
        distances,
        strengths,
        charges;

    function repulse(node) {
      return function (quad, x1, _, x2) {
        if (quad.point !== node) {
          var dx = quad.cx - node.x,
              dy = quad.cy - node.y,
              dn = 1 / Math.sqrt(dx * dx + dy * dy);

          if ((x2 - x1) * dn < theta) {
            var k = quad.charge * dn * dn;
            node.px -= dx * k;
            node.py -= dy * k;
            return true;
          }

          if (quad.point && isFinite(dn)) {
            var k = quad.pointCharge * dn * dn;
            node.px -= dx * k;
            node.py -= dy * k;
          }
        }

        return !quad.charge;
      };
    }

    force.tick = function () {
      if ((alpha *= .99) < .005) {
        event.end({
          type: "end",
          alpha: alpha = 0
        });
        return true;
      }

      var n = nodes.length,
          m = links.length,
          q,
          i,
          o,
          s,
          t,
          l,
          k,
          x,
          y;

      for (i = 0; i < m; ++i) {
        o = links[i];
        s = o.source;
        t = o.target;
        x = t.x - s.x;
        y = t.y - s.y;

        if (l = x * x + y * y) {
          l = alpha * strengths[i] * ((l = Math.sqrt(l)) - distances[i]) / l;
          x *= l;
          y *= l;
          t.x -= x * (k = s.weight / (t.weight + s.weight));
          t.y -= y * k;
          s.x += x * (k = 1 - k);
          s.y += y * k;
        }
      }

      if (k = alpha * gravity) {
        x = size[0] / 2;
        y = size[1] / 2;
        i = -1;
        if (k) while (++i < n) {
          o = nodes[i];
          o.x += (x - o.x) * k;
          o.y += (y - o.y) * k;
        }
      }

      if (charge) {
        d3_layout_forceAccumulate(q = d3.geom.quadtree(nodes), alpha, charges);
        i = -1;

        while (++i < n) {
          if (!(o = nodes[i]).fixed) {
            q.visit(repulse(o));
          }
        }
      }

      i = -1;

      while (++i < n) {
        o = nodes[i];

        if (o.fixed) {
          o.x = o.px;
          o.y = o.py;
        } else {
          o.x -= (o.px - (o.px = o.x)) * friction;
          o.y -= (o.py - (o.py = o.y)) * friction;
        }
      }

      event.tick({
        type: "tick",
        alpha: alpha
      });
    };

    force.nodes = function (x) {
      if (!arguments.length) return nodes;
      nodes = x;
      return force;
    };

    force.links = function (x) {
      if (!arguments.length) return links;
      links = x;
      return force;
    };

    force.size = function (x) {
      if (!arguments.length) return size;
      size = x;
      return force;
    };

    force.linkDistance = function (x) {
      if (!arguments.length) return linkDistance;
      linkDistance = typeof x === "function" ? x : +x;
      return force;
    };

    force.distance = force.linkDistance;

    force.linkStrength = function (x) {
      if (!arguments.length) return linkStrength;
      linkStrength = typeof x === "function" ? x : +x;
      return force;
    };

    force.friction = function (x) {
      if (!arguments.length) return friction;
      friction = +x;
      return force;
    };

    force.charge = function (x) {
      if (!arguments.length) return charge;
      charge = typeof x === "function" ? x : +x;
      return force;
    };

    force.gravity = function (x) {
      if (!arguments.length) return gravity;
      gravity = +x;
      return force;
    };

    force.theta = function (x) {
      if (!arguments.length) return theta;
      theta = +x;
      return force;
    };

    force.alpha = function (x) {
      if (!arguments.length) return alpha;
      x = +x;

      if (alpha) {
        if (x > 0) alpha = x;else alpha = 0;
      } else if (x > 0) {
        event.start({
          type: "start",
          alpha: alpha = x
        });
        d3.timer(force.tick);
      }

      return force;
    };

    force.start = function () {
      var i,
          j,
          n = nodes.length,
          m = links.length,
          w = size[0],
          h = size[1],
          neighbors,
          o;

      for (i = 0; i < n; ++i) {
        (o = nodes[i]).index = i;
        o.weight = 0;
      }

      for (i = 0; i < m; ++i) {
        o = links[i];
        if (typeof o.source == "number") o.source = nodes[o.source];
        if (typeof o.target == "number") o.target = nodes[o.target];
        ++o.source.weight;
        ++o.target.weight;
      }

      for (i = 0; i < n; ++i) {
        o = nodes[i];
        if (isNaN(o.x)) o.x = position("x", w);
        if (isNaN(o.y)) o.y = position("y", h);
        if (isNaN(o.px)) o.px = o.x;
        if (isNaN(o.py)) o.py = o.y;
      }

      distances = [];
      if (typeof linkDistance === "function") for (i = 0; i < m; ++i) {
        distances[i] = +linkDistance.call(this, links[i], i);
      } else for (i = 0; i < m; ++i) {
        distances[i] = linkDistance;
      }
      strengths = [];
      if (typeof linkStrength === "function") for (i = 0; i < m; ++i) {
        strengths[i] = +linkStrength.call(this, links[i], i);
      } else for (i = 0; i < m; ++i) {
        strengths[i] = linkStrength;
      }
      charges = [];
      if (typeof charge === "function") for (i = 0; i < n; ++i) {
        charges[i] = +charge.call(this, nodes[i], i);
      } else for (i = 0; i < n; ++i) {
        charges[i] = charge;
      }

      function position(dimension, size) {
        var neighbors = neighbor(i),
            j = -1,
            m = neighbors.length,
            x;

        while (++j < m) {
          if (!isNaN(x = neighbors[j][dimension])) return x;
        }

        return Math.random() * size;
      }

      function neighbor() {
        if (!neighbors) {
          neighbors = [];

          for (j = 0; j < n; ++j) {
            neighbors[j] = [];
          }

          for (j = 0; j < m; ++j) {
            var o = links[j];
            neighbors[o.source.index].push(o.target);
            neighbors[o.target.index].push(o.source);
          }
        }

        return neighbors[i];
      }

      return force.resume();
    };

    force.resume = function () {
      return force.alpha(.1);
    };

    force.stop = function () {
      return force.alpha(0);
    };

    force.drag = function () {
      if (!drag) drag = d3.behavior.drag().origin(d3_identity).on("dragstart.force", d3_layout_forceDragstart).on("drag.force", dragmove).on("dragend.force", d3_layout_forceDragend);
      if (!arguments.length) return drag;
      this.on("mouseover.force", d3_layout_forceMouseover).on("mouseout.force", d3_layout_forceMouseout).call(drag);
    };

    function dragmove(d) {
      d.px = d3.event.x, d.py = d3.event.y;
      force.resume();
    }

    return d3.rebind(force, event, "on");
  };

  function d3_layout_forceDragstart(d) {
    d.fixed |= 2;
  }

  function d3_layout_forceDragend(d) {
    d.fixed &= ~6;
  }

  function d3_layout_forceMouseover(d) {
    d.fixed |= 4;
    d.px = d.x, d.py = d.y;
  }

  function d3_layout_forceMouseout(d) {
    d.fixed &= ~4;
  }

  function d3_layout_forceAccumulate(quad, alpha, charges) {
    var cx = 0,
        cy = 0;
    quad.charge = 0;

    if (!quad.leaf) {
      var nodes = quad.nodes,
          n = nodes.length,
          i = -1,
          c;

      while (++i < n) {
        c = nodes[i];
        if (c == null) continue;
        d3_layout_forceAccumulate(c, alpha, charges);
        quad.charge += c.charge;
        cx += c.charge * c.cx;
        cy += c.charge * c.cy;
      }
    }

    if (quad.point) {
      if (!quad.leaf) {
        quad.point.x += Math.random() - .5;
        quad.point.y += Math.random() - .5;
      }

      var k = alpha * charges[quad.point.index];
      quad.charge += quad.pointCharge = k;
      cx += k * quad.point.x;
      cy += k * quad.point.y;
    }

    quad.cx = cx / quad.charge;
    quad.cy = cy / quad.charge;
  }

  var d3_layout_forceLinkDistance = 20,
      d3_layout_forceLinkStrength = 1;

  d3.layout.hierarchy = function () {
    var sort = d3_layout_hierarchySort,
        children = d3_layout_hierarchyChildren,
        value = d3_layout_hierarchyValue;

    function recurse(node, depth, nodes) {
      var childs = children.call(hierarchy, node, depth);
      node.depth = depth;
      nodes.push(node);

      if (childs && (n = childs.length)) {
        var i = -1,
            n,
            c = node.children = [],
            v = 0,
            j = depth + 1,
            d;

        while (++i < n) {
          d = recurse(childs[i], j, nodes);
          d.parent = node;
          c.push(d);
          v += d.value;
        }

        if (sort) c.sort(sort);
        if (value) node.value = v;
      } else if (value) {
        node.value = +value.call(hierarchy, node, depth) || 0;
      }

      return node;
    }

    function revalue(node, depth) {
      var children = node.children,
          v = 0;

      if (children && (n = children.length)) {
        var i = -1,
            n,
            j = depth + 1;

        while (++i < n) {
          v += revalue(children[i], j);
        }
      } else if (value) {
        v = +value.call(hierarchy, node, depth) || 0;
      }

      if (value) node.value = v;
      return v;
    }

    function hierarchy(d) {
      var nodes = [];
      recurse(d, 0, nodes);
      return nodes;
    }

    hierarchy.sort = function (x) {
      if (!arguments.length) return sort;
      sort = x;
      return hierarchy;
    };

    hierarchy.children = function (x) {
      if (!arguments.length) return children;
      children = x;
      return hierarchy;
    };

    hierarchy.value = function (x) {
      if (!arguments.length) return value;
      value = x;
      return hierarchy;
    };

    hierarchy.revalue = function (root) {
      revalue(root, 0);
      return root;
    };

    return hierarchy;
  };

  function d3_layout_hierarchyRebind(object, hierarchy) {
    d3.rebind(object, hierarchy, "sort", "children", "value");
    object.nodes = object;
    object.links = d3_layout_hierarchyLinks;
    return object;
  }

  function d3_layout_hierarchyChildren(d) {
    return d.children;
  }

  function d3_layout_hierarchyValue(d) {
    return d.value;
  }

  function d3_layout_hierarchySort(a, b) {
    return b.value - a.value;
  }

  function d3_layout_hierarchyLinks(nodes) {
    return d3.merge(nodes.map(function (parent) {
      return (parent.children || []).map(function (child) {
        return {
          source: parent,
          target: child
        };
      });
    }));
  }

  d3.layout.partition = function () {
    var hierarchy = d3.layout.hierarchy(),
        size = [1, 1];

    function position(node, x, dx, dy) {
      var children = node.children;
      node.x = x;
      node.y = node.depth * dy;
      node.dx = dx;
      node.dy = dy;

      if (children && (n = children.length)) {
        var i = -1,
            n,
            c,
            d;
        dx = node.value ? dx / node.value : 0;

        while (++i < n) {
          position(c = children[i], x, d = c.value * dx, dy);
          x += d;
        }
      }
    }

    function depth(node) {
      var children = node.children,
          d = 0;

      if (children && (n = children.length)) {
        var i = -1,
            n;

        while (++i < n) {
          d = Math.max(d, depth(children[i]));
        }
      }

      return 1 + d;
    }

    function partition(d, i) {
      var nodes = hierarchy.call(this, d, i);
      position(nodes[0], 0, size[0], size[1] / depth(nodes[0]));
      return nodes;
    }

    partition.size = function (x) {
      if (!arguments.length) return size;
      size = x;
      return partition;
    };

    return d3_layout_hierarchyRebind(partition, hierarchy);
  };

  d3.layout.pie = function () {
    var value = Number,
        sort = d3_layout_pieSortByValue,
        startAngle = 0,
        endAngle = 2 * π;

    function pie(data) {
      var values = data.map(function (d, i) {
        return +value.call(pie, d, i);
      });
      var a = +(typeof startAngle === "function" ? startAngle.apply(this, arguments) : startAngle);
      var k = ((typeof endAngle === "function" ? endAngle.apply(this, arguments) : endAngle) - a) / d3.sum(values);
      var index = d3.range(data.length);
      if (sort != null) index.sort(sort === d3_layout_pieSortByValue ? function (i, j) {
        return values[j] - values[i];
      } : function (i, j) {
        return sort(data[i], data[j]);
      });
      var arcs = [];
      index.forEach(function (i) {
        var d;
        arcs[i] = {
          data: data[i],
          value: d = values[i],
          startAngle: a,
          endAngle: a += d * k
        };
      });
      return arcs;
    }

    pie.value = function (x) {
      if (!arguments.length) return value;
      value = x;
      return pie;
    };

    pie.sort = function (x) {
      if (!arguments.length) return sort;
      sort = x;
      return pie;
    };

    pie.startAngle = function (x) {
      if (!arguments.length) return startAngle;
      startAngle = x;
      return pie;
    };

    pie.endAngle = function (x) {
      if (!arguments.length) return endAngle;
      endAngle = x;
      return pie;
    };

    return pie;
  };

  var d3_layout_pieSortByValue = {};

  d3.layout.stack = function () {
    var values = d3_identity,
        order = d3_layout_stackOrderDefault,
        offset = d3_layout_stackOffsetZero,
        out = d3_layout_stackOut,
        x = d3_layout_stackX,
        y = d3_layout_stackY;

    function stack(data, index) {
      var series = data.map(function (d, i) {
        return values.call(stack, d, i);
      });
      var points = series.map(function (d) {
        return d.map(function (v, i) {
          return [x.call(stack, v, i), y.call(stack, v, i)];
        });
      });
      var orders = order.call(stack, points, index);
      series = d3.permute(series, orders);
      points = d3.permute(points, orders);
      var offsets = offset.call(stack, points, index);
      var n = series.length,
          m = series[0].length,
          i,
          j,
          o;

      for (j = 0; j < m; ++j) {
        out.call(stack, series[0][j], o = offsets[j], points[0][j][1]);

        for (i = 1; i < n; ++i) {
          out.call(stack, series[i][j], o += points[i - 1][j][1], points[i][j][1]);
        }
      }

      return data;
    }

    stack.values = function (x) {
      if (!arguments.length) return values;
      values = x;
      return stack;
    };

    stack.order = function (x) {
      if (!arguments.length) return order;
      order = typeof x === "function" ? x : d3_layout_stackOrders.get(x) || d3_layout_stackOrderDefault;
      return stack;
    };

    stack.offset = function (x) {
      if (!arguments.length) return offset;
      offset = typeof x === "function" ? x : d3_layout_stackOffsets.get(x) || d3_layout_stackOffsetZero;
      return stack;
    };

    stack.x = function (z) {
      if (!arguments.length) return x;
      x = z;
      return stack;
    };

    stack.y = function (z) {
      if (!arguments.length) return y;
      y = z;
      return stack;
    };

    stack.out = function (z) {
      if (!arguments.length) return out;
      out = z;
      return stack;
    };

    return stack;
  };

  function d3_layout_stackX(d) {
    return d.x;
  }

  function d3_layout_stackY(d) {
    return d.y;
  }

  function d3_layout_stackOut(d, y0, y) {
    d.y0 = y0;
    d.y = y;
  }

  var d3_layout_stackOrders = d3.map({
    "inside-out": function insideOut(data) {
      var n = data.length,
          i,
          j,
          max = data.map(d3_layout_stackMaxIndex),
          sums = data.map(d3_layout_stackReduceSum),
          index = d3.range(n).sort(function (a, b) {
        return max[a] - max[b];
      }),
          top = 0,
          bottom = 0,
          tops = [],
          bottoms = [];

      for (i = 0; i < n; ++i) {
        j = index[i];

        if (top < bottom) {
          top += sums[j];
          tops.push(j);
        } else {
          bottom += sums[j];
          bottoms.push(j);
        }
      }

      return bottoms.reverse().concat(tops);
    },
    reverse: function reverse(data) {
      return d3.range(data.length).reverse();
    },
    "default": d3_layout_stackOrderDefault
  });
  var d3_layout_stackOffsets = d3.map({
    silhouette: function silhouette(data) {
      var n = data.length,
          m = data[0].length,
          sums = [],
          max = 0,
          i,
          j,
          o,
          y0 = [];

      for (j = 0; j < m; ++j) {
        for (i = 0, o = 0; i < n; i++) {
          o += data[i][j][1];
        }

        if (o > max) max = o;
        sums.push(o);
      }

      for (j = 0; j < m; ++j) {
        y0[j] = (max - sums[j]) / 2;
      }

      return y0;
    },
    wiggle: function wiggle(data) {
      var n = data.length,
          x = data[0],
          m = x.length,
          i,
          j,
          k,
          s1,
          s2,
          s3,
          dx,
          o,
          o0,
          y0 = [];
      y0[0] = o = o0 = 0;

      for (j = 1; j < m; ++j) {
        for (i = 0, s1 = 0; i < n; ++i) {
          s1 += data[i][j][1];
        }

        for (i = 0, s2 = 0, dx = x[j][0] - x[j - 1][0]; i < n; ++i) {
          for (k = 0, s3 = (data[i][j][1] - data[i][j - 1][1]) / (2 * dx); k < i; ++k) {
            s3 += (data[k][j][1] - data[k][j - 1][1]) / dx;
          }

          s2 += s3 * data[i][j][1];
        }

        y0[j] = o -= s1 ? s2 / s1 * dx : 0;
        if (o < o0) o0 = o;
      }

      for (j = 0; j < m; ++j) {
        y0[j] -= o0;
      }

      return y0;
    },
    expand: function expand(data) {
      var n = data.length,
          m = data[0].length,
          k = 1 / n,
          i,
          j,
          o,
          y0 = [];

      for (j = 0; j < m; ++j) {
        for (i = 0, o = 0; i < n; i++) {
          o += data[i][j][1];
        }

        if (o) for (i = 0; i < n; i++) {
          data[i][j][1] /= o;
        } else for (i = 0; i < n; i++) {
          data[i][j][1] = k;
        }
      }

      for (j = 0; j < m; ++j) {
        y0[j] = 0;
      }

      return y0;
    },
    zero: d3_layout_stackOffsetZero
  });

  function d3_layout_stackOrderDefault(data) {
    return d3.range(data.length);
  }

  function d3_layout_stackOffsetZero(data) {
    var j = -1,
        m = data[0].length,
        y0 = [];

    while (++j < m) {
      y0[j] = 0;
    }

    return y0;
  }

  function d3_layout_stackMaxIndex(array) {
    var i = 1,
        j = 0,
        v = array[0][1],
        k,
        n = array.length;

    for (; i < n; ++i) {
      if ((k = array[i][1]) > v) {
        j = i;
        v = k;
      }
    }

    return j;
  }

  function d3_layout_stackReduceSum(d) {
    return d.reduce(d3_layout_stackSum, 0);
  }

  function d3_layout_stackSum(p, d) {
    return p + d[1];
  }

  d3.layout.histogram = function () {
    var frequency = true,
        valuer = Number,
        ranger = d3_layout_histogramRange,
        binner = d3_layout_histogramBinSturges;

    function histogram(data, i) {
      var bins = [],
          values = data.map(valuer, this),
          range = ranger.call(this, values, i),
          thresholds = binner.call(this, range, values, i),
          bin,
          i = -1,
          n = values.length,
          m = thresholds.length - 1,
          k = frequency ? 1 : 1 / n,
          x;

      while (++i < m) {
        bin = bins[i] = [];
        bin.dx = thresholds[i + 1] - (bin.x = thresholds[i]);
        bin.y = 0;
      }

      if (m > 0) {
        i = -1;

        while (++i < n) {
          x = values[i];

          if (x >= range[0] && x <= range[1]) {
            bin = bins[d3.bisect(thresholds, x, 1, m) - 1];
            bin.y += k;
            bin.push(data[i]);
          }
        }
      }

      return bins;
    }

    histogram.value = function (x) {
      if (!arguments.length) return valuer;
      valuer = x;
      return histogram;
    };

    histogram.range = function (x) {
      if (!arguments.length) return ranger;
      ranger = d3_functor(x);
      return histogram;
    };

    histogram.bins = function (x) {
      if (!arguments.length) return binner;
      binner = typeof x === "number" ? function (range) {
        return d3_layout_histogramBinFixed(range, x);
      } : d3_functor(x);
      return histogram;
    };

    histogram.frequency = function (x) {
      if (!arguments.length) return frequency;
      frequency = !!x;
      return histogram;
    };

    return histogram;
  };

  function d3_layout_histogramBinSturges(range, values) {
    return d3_layout_histogramBinFixed(range, Math.ceil(Math.log(values.length) / Math.LN2 + 1));
  }

  function d3_layout_histogramBinFixed(range, n) {
    var x = -1,
        b = +range[0],
        m = (range[1] - b) / n,
        f = [];

    while (++x <= n) {
      f[x] = m * x + b;
    }

    return f;
  }

  function d3_layout_histogramRange(values) {
    return [d3.min(values), d3.max(values)];
  }

  d3.layout.tree = function () {
    var hierarchy = d3.layout.hierarchy().sort(null).value(null),
        separation = d3_layout_treeSeparation,
        size = [1, 1];

    function tree(d, i) {
      var nodes = hierarchy.call(this, d, i),
          root = nodes[0];

      function firstWalk(node, previousSibling) {
        var children = node.children,
            layout = node._tree;

        if (children && (n = children.length)) {
          var n,
              firstChild = children[0],
              previousChild,
              ancestor = firstChild,
              child,
              i = -1;

          while (++i < n) {
            child = children[i];
            firstWalk(child, previousChild);
            ancestor = apportion(child, previousChild, ancestor);
            previousChild = child;
          }

          d3_layout_treeShift(node);
          var midpoint = .5 * (firstChild._tree.prelim + child._tree.prelim);

          if (previousSibling) {
            layout.prelim = previousSibling._tree.prelim + separation(node, previousSibling);
            layout.mod = layout.prelim - midpoint;
          } else {
            layout.prelim = midpoint;
          }
        } else {
          if (previousSibling) {
            layout.prelim = previousSibling._tree.prelim + separation(node, previousSibling);
          }
        }
      }

      function secondWalk(node, x) {
        node.x = node._tree.prelim + x;
        var children = node.children;

        if (children && (n = children.length)) {
          var i = -1,
              n;
          x += node._tree.mod;

          while (++i < n) {
            secondWalk(children[i], x);
          }
        }
      }

      function apportion(node, previousSibling, ancestor) {
        if (previousSibling) {
          var vip = node,
              vop = node,
              vim = previousSibling,
              vom = node.parent.children[0],
              sip = vip._tree.mod,
              sop = vop._tree.mod,
              sim = vim._tree.mod,
              som = vom._tree.mod,
              shift;

          while (vim = d3_layout_treeRight(vim), vip = d3_layout_treeLeft(vip), vim && vip) {
            vom = d3_layout_treeLeft(vom);
            vop = d3_layout_treeRight(vop);
            vop._tree.ancestor = node;
            shift = vim._tree.prelim + sim - vip._tree.prelim - sip + separation(vim, vip);

            if (shift > 0) {
              d3_layout_treeMove(d3_layout_treeAncestor(vim, node, ancestor), node, shift);
              sip += shift;
              sop += shift;
            }

            sim += vim._tree.mod;
            sip += vip._tree.mod;
            som += vom._tree.mod;
            sop += vop._tree.mod;
          }

          if (vim && !d3_layout_treeRight(vop)) {
            vop._tree.thread = vim;
            vop._tree.mod += sim - sop;
          }

          if (vip && !d3_layout_treeLeft(vom)) {
            vom._tree.thread = vip;
            vom._tree.mod += sip - som;
            ancestor = node;
          }
        }

        return ancestor;
      }

      d3_layout_treeVisitAfter(root, function (node, previousSibling) {
        node._tree = {
          ancestor: node,
          prelim: 0,
          mod: 0,
          change: 0,
          shift: 0,
          number: previousSibling ? previousSibling._tree.number + 1 : 0
        };
      });
      firstWalk(root);
      secondWalk(root, -root._tree.prelim);
      var left = d3_layout_treeSearch(root, d3_layout_treeLeftmost),
          right = d3_layout_treeSearch(root, d3_layout_treeRightmost),
          deep = d3_layout_treeSearch(root, d3_layout_treeDeepest),
          x0 = left.x - separation(left, right) / 2,
          x1 = right.x + separation(right, left) / 2,
          y1 = deep.depth || 1;
      d3_layout_treeVisitAfter(root, function (node) {
        node.x = (node.x - x0) / (x1 - x0) * size[0];
        node.y = node.depth / y1 * size[1];
        delete node._tree;
      });
      return nodes;
    }

    tree.separation = function (x) {
      if (!arguments.length) return separation;
      separation = x;
      return tree;
    };

    tree.size = function (x) {
      if (!arguments.length) return size;
      size = x;
      return tree;
    };

    return d3_layout_hierarchyRebind(tree, hierarchy);
  };

  function d3_layout_treeSeparation(a, b) {
    return a.parent == b.parent ? 1 : 2;
  }

  function d3_layout_treeLeft(node) {
    var children = node.children;
    return children && children.length ? children[0] : node._tree.thread;
  }

  function d3_layout_treeRight(node) {
    var children = node.children,
        n;
    return children && (n = children.length) ? children[n - 1] : node._tree.thread;
  }

  function d3_layout_treeSearch(node, compare) {
    var children = node.children;

    if (children && (n = children.length)) {
      var child,
          n,
          i = -1;

      while (++i < n) {
        if (compare(child = d3_layout_treeSearch(children[i], compare), node) > 0) {
          node = child;
        }
      }
    }

    return node;
  }

  function d3_layout_treeRightmost(a, b) {
    return a.x - b.x;
  }

  function d3_layout_treeLeftmost(a, b) {
    return b.x - a.x;
  }

  function d3_layout_treeDeepest(a, b) {
    return a.depth - b.depth;
  }

  function d3_layout_treeVisitAfter(node, callback) {
    function visit(node, previousSibling) {
      var children = node.children;

      if (children && (n = children.length)) {
        var child,
            previousChild = null,
            i = -1,
            n;

        while (++i < n) {
          child = children[i];
          visit(child, previousChild);
          previousChild = child;
        }
      }

      callback(node, previousSibling);
    }

    visit(node, null);
  }

  function d3_layout_treeShift(node) {
    var shift = 0,
        change = 0,
        children = node.children,
        i = children.length,
        child;

    while (--i >= 0) {
      child = children[i]._tree;
      child.prelim += shift;
      child.mod += shift;
      shift += child.shift + (change += child.change);
    }
  }

  function d3_layout_treeMove(ancestor, node, shift) {
    ancestor = ancestor._tree;
    node = node._tree;
    var change = shift / (node.number - ancestor.number);
    ancestor.change += change;
    node.change -= change;
    node.shift += shift;
    node.prelim += shift;
    node.mod += shift;
  }

  function d3_layout_treeAncestor(vim, node, ancestor) {
    return vim._tree.ancestor.parent == node.parent ? vim._tree.ancestor : ancestor;
  }

  d3.layout.pack = function () {
    var hierarchy = d3.layout.hierarchy().sort(d3_layout_packSort),
        padding = 0,
        size = [1, 1];

    function pack(d, i) {
      var nodes = hierarchy.call(this, d, i),
          root = nodes[0];
      root.x = 0;
      root.y = 0;
      d3_layout_treeVisitAfter(root, function (d) {
        d.r = Math.sqrt(d.value);
      });
      d3_layout_treeVisitAfter(root, d3_layout_packSiblings);
      var w = size[0],
          h = size[1],
          k = Math.max(2 * root.r / w, 2 * root.r / h);

      if (padding > 0) {
        var dr = padding * k / 2;
        d3_layout_treeVisitAfter(root, function (d) {
          d.r += dr;
        });
        d3_layout_treeVisitAfter(root, d3_layout_packSiblings);
        d3_layout_treeVisitAfter(root, function (d) {
          d.r -= dr;
        });
        k = Math.max(2 * root.r / w, 2 * root.r / h);
      }

      d3_layout_packTransform(root, w / 2, h / 2, 1 / k);
      return nodes;
    }

    pack.size = function (x) {
      if (!arguments.length) return size;
      size = x;
      return pack;
    };

    pack.padding = function (_) {
      if (!arguments.length) return padding;
      padding = +_;
      return pack;
    };

    return d3_layout_hierarchyRebind(pack, hierarchy);
  };

  function d3_layout_packSort(a, b) {
    return a.value - b.value;
  }

  function d3_layout_packInsert(a, b) {
    var c = a._pack_next;
    a._pack_next = b;
    b._pack_prev = a;
    b._pack_next = c;
    c._pack_prev = b;
  }

  function d3_layout_packSplice(a, b) {
    a._pack_next = b;
    b._pack_prev = a;
  }

  function d3_layout_packIntersects(a, b) {
    var dx = b.x - a.x,
        dy = b.y - a.y,
        dr = a.r + b.r;
    return dr * dr - dx * dx - dy * dy > .001;
  }

  function d3_layout_packSiblings(node) {
    if (!(nodes = node.children) || !(n = nodes.length)) return;
    var nodes,
        xMin = Infinity,
        xMax = -Infinity,
        yMin = Infinity,
        yMax = -Infinity,
        a,
        b,
        c,
        i,
        j,
        k,
        n;

    function bound(node) {
      xMin = Math.min(node.x - node.r, xMin);
      xMax = Math.max(node.x + node.r, xMax);
      yMin = Math.min(node.y - node.r, yMin);
      yMax = Math.max(node.y + node.r, yMax);
    }

    nodes.forEach(d3_layout_packLink);
    a = nodes[0];
    a.x = -a.r;
    a.y = 0;
    bound(a);

    if (n > 1) {
      b = nodes[1];
      b.x = b.r;
      b.y = 0;
      bound(b);

      if (n > 2) {
        c = nodes[2];
        d3_layout_packPlace(a, b, c);
        bound(c);
        d3_layout_packInsert(a, c);
        a._pack_prev = c;
        d3_layout_packInsert(c, b);
        b = a._pack_next;

        for (i = 3; i < n; i++) {
          d3_layout_packPlace(a, b, c = nodes[i]);
          var isect = 0,
              s1 = 1,
              s2 = 1;

          for (j = b._pack_next; j !== b; j = j._pack_next, s1++) {
            if (d3_layout_packIntersects(j, c)) {
              isect = 1;
              break;
            }
          }

          if (isect == 1) {
            for (k = a._pack_prev; k !== j._pack_prev; k = k._pack_prev, s2++) {
              if (d3_layout_packIntersects(k, c)) {
                break;
              }
            }
          }

          if (isect) {
            if (s1 < s2 || s1 == s2 && b.r < a.r) d3_layout_packSplice(a, b = j);else d3_layout_packSplice(a = k, b);
            i--;
          } else {
            d3_layout_packInsert(a, c);
            b = c;
            bound(c);
          }
        }
      }
    }

    var cx = (xMin + xMax) / 2,
        cy = (yMin + yMax) / 2,
        cr = 0;

    for (i = 0; i < n; i++) {
      c = nodes[i];
      c.x -= cx;
      c.y -= cy;
      cr = Math.max(cr, c.r + Math.sqrt(c.x * c.x + c.y * c.y));
    }

    node.r = cr;
    nodes.forEach(d3_layout_packUnlink);
  }

  function d3_layout_packLink(node) {
    node._pack_next = node._pack_prev = node;
  }

  function d3_layout_packUnlink(node) {
    delete node._pack_next;
    delete node._pack_prev;
  }

  function d3_layout_packTransform(node, x, y, k) {
    var children = node.children;
    node.x = x += k * node.x;
    node.y = y += k * node.y;
    node.r *= k;

    if (children) {
      var i = -1,
          n = children.length;

      while (++i < n) {
        d3_layout_packTransform(children[i], x, y, k);
      }
    }
  }

  function d3_layout_packPlace(a, b, c) {
    var db = a.r + c.r,
        dx = b.x - a.x,
        dy = b.y - a.y;

    if (db && (dx || dy)) {
      var da = b.r + c.r,
          dc = dx * dx + dy * dy;
      da *= da;
      db *= db;
      var x = .5 + (db - da) / (2 * dc),
          y = Math.sqrt(Math.max(0, 2 * da * (db + dc) - (db -= dc) * db - da * da)) / (2 * dc);
      c.x = a.x + x * dx + y * dy;
      c.y = a.y + x * dy - y * dx;
    } else {
      c.x = a.x + db;
      c.y = a.y;
    }
  }

  d3.layout.cluster = function () {
    var hierarchy = d3.layout.hierarchy().sort(null).value(null),
        separation = d3_layout_treeSeparation,
        size = [1, 1];

    function cluster(d, i) {
      var nodes = hierarchy.call(this, d, i),
          root = nodes[0],
          previousNode,
          x = 0;
      d3_layout_treeVisitAfter(root, function (node) {
        var children = node.children;

        if (children && children.length) {
          node.x = d3_layout_clusterX(children);
          node.y = d3_layout_clusterY(children);
        } else {
          node.x = previousNode ? x += separation(node, previousNode) : 0;
          node.y = 0;
          previousNode = node;
        }
      });
      var left = d3_layout_clusterLeft(root),
          right = d3_layout_clusterRight(root),
          x0 = left.x - separation(left, right) / 2,
          x1 = right.x + separation(right, left) / 2;
      d3_layout_treeVisitAfter(root, function (node) {
        node.x = (node.x - x0) / (x1 - x0) * size[0];
        node.y = (1 - (root.y ? node.y / root.y : 1)) * size[1];
      });
      return nodes;
    }

    cluster.separation = function (x) {
      if (!arguments.length) return separation;
      separation = x;
      return cluster;
    };

    cluster.size = function (x) {
      if (!arguments.length) return size;
      size = x;
      return cluster;
    };

    return d3_layout_hierarchyRebind(cluster, hierarchy);
  };

  function d3_layout_clusterY(children) {
    return 1 + d3.max(children, function (child) {
      return child.y;
    });
  }

  function d3_layout_clusterX(children) {
    return children.reduce(function (x, child) {
      return x + child.x;
    }, 0) / children.length;
  }

  function d3_layout_clusterLeft(node) {
    var children = node.children;
    return children && children.length ? d3_layout_clusterLeft(children[0]) : node;
  }

  function d3_layout_clusterRight(node) {
    var children = node.children,
        n;
    return children && (n = children.length) ? d3_layout_clusterRight(children[n - 1]) : node;
  }

  d3.layout.treemap = function () {
    var hierarchy = d3.layout.hierarchy(),
        round = Math.round,
        size = [1, 1],
        padding = null,
        pad = d3_layout_treemapPadNull,
        sticky = false,
        stickies,
        mode = "squarify",
        ratio = .5 * (1 + Math.sqrt(5));

    function scale(children, k) {
      var i = -1,
          n = children.length,
          child,
          area;

      while (++i < n) {
        area = (child = children[i]).value * (k < 0 ? 0 : k);
        child.area = isNaN(area) || area <= 0 ? 0 : area;
      }
    }

    function squarify(node) {
      var children = node.children;

      if (children && children.length) {
        var rect = pad(node),
            row = [],
            remaining = children.slice(),
            child,
            best = Infinity,
            score,
            u = mode === "slice" ? rect.dx : mode === "dice" ? rect.dy : mode === "slice-dice" ? node.depth & 1 ? rect.dy : rect.dx : Math.min(rect.dx, rect.dy),
            n;
        scale(remaining, rect.dx * rect.dy / node.value);
        row.area = 0;

        while ((n = remaining.length) > 0) {
          row.push(child = remaining[n - 1]);
          row.area += child.area;

          if (mode !== "squarify" || (score = worst(row, u)) <= best) {
            remaining.pop();
            best = score;
          } else {
            row.area -= row.pop().area;
            position(row, u, rect, false);
            u = Math.min(rect.dx, rect.dy);
            row.length = row.area = 0;
            best = Infinity;
          }
        }

        if (row.length) {
          position(row, u, rect, true);
          row.length = row.area = 0;
        }

        children.forEach(squarify);
      }
    }

    function stickify(node) {
      var children = node.children;

      if (children && children.length) {
        var rect = pad(node),
            remaining = children.slice(),
            child,
            row = [];
        scale(remaining, rect.dx * rect.dy / node.value);
        row.area = 0;

        while (child = remaining.pop()) {
          row.push(child);
          row.area += child.area;

          if (child.z != null) {
            position(row, child.z ? rect.dx : rect.dy, rect, !remaining.length);
            row.length = row.area = 0;
          }
        }

        children.forEach(stickify);
      }
    }

    function worst(row, u) {
      var s = row.area,
          r,
          rmax = 0,
          rmin = Infinity,
          i = -1,
          n = row.length;

      while (++i < n) {
        if (!(r = row[i].area)) continue;
        if (r < rmin) rmin = r;
        if (r > rmax) rmax = r;
      }

      s *= s;
      u *= u;
      return s ? Math.max(u * rmax * ratio / s, s / (u * rmin * ratio)) : Infinity;
    }

    function position(row, u, rect, flush) {
      var i = -1,
          n = row.length,
          x = rect.x,
          y = rect.y,
          v = u ? round(row.area / u) : 0,
          o;

      if (u == rect.dx) {
        if (flush || v > rect.dy) v = rect.dy;

        while (++i < n) {
          o = row[i];
          o.x = x;
          o.y = y;
          o.dy = v;
          x += o.dx = Math.min(rect.x + rect.dx - x, v ? round(o.area / v) : 0);
        }

        o.z = true;
        o.dx += rect.x + rect.dx - x;
        rect.y += v;
        rect.dy -= v;
      } else {
        if (flush || v > rect.dx) v = rect.dx;

        while (++i < n) {
          o = row[i];
          o.x = x;
          o.y = y;
          o.dx = v;
          y += o.dy = Math.min(rect.y + rect.dy - y, v ? round(o.area / v) : 0);
        }

        o.z = false;
        o.dy += rect.y + rect.dy - y;
        rect.x += v;
        rect.dx -= v;
      }
    }

    function treemap(d) {
      var nodes = stickies || hierarchy(d),
          root = nodes[0];
      root.x = 0;
      root.y = 0;
      root.dx = size[0];
      root.dy = size[1];
      if (stickies) hierarchy.revalue(root);
      scale([root], root.dx * root.dy / root.value);
      (stickies ? stickify : squarify)(root);
      if (sticky) stickies = nodes;
      return nodes;
    }

    treemap.size = function (x) {
      if (!arguments.length) return size;
      size = x;
      return treemap;
    };

    treemap.padding = function (x) {
      if (!arguments.length) return padding;

      function padFunction(node) {
        var p = x.call(treemap, node, node.depth);
        return p == null ? d3_layout_treemapPadNull(node) : d3_layout_treemapPad(node, typeof p === "number" ? [p, p, p, p] : p);
      }

      function padConstant(node) {
        return d3_layout_treemapPad(node, x);
      }

      var type;
      pad = (padding = x) == null ? d3_layout_treemapPadNull : (type = _typeof(x)) === "function" ? padFunction : type === "number" ? (x = [x, x, x, x], padConstant) : padConstant;
      return treemap;
    };

    treemap.round = function (x) {
      if (!arguments.length) return round != Number;
      round = x ? Math.round : Number;
      return treemap;
    };

    treemap.sticky = function (x) {
      if (!arguments.length) return sticky;
      sticky = x;
      stickies = null;
      return treemap;
    };

    treemap.ratio = function (x) {
      if (!arguments.length) return ratio;
      ratio = x;
      return treemap;
    };

    treemap.mode = function (x) {
      if (!arguments.length) return mode;
      mode = x + "";
      return treemap;
    };

    return d3_layout_hierarchyRebind(treemap, hierarchy);
  };

  function d3_layout_treemapPadNull(node) {
    return {
      x: node.x,
      y: node.y,
      dx: node.dx,
      dy: node.dy
    };
  }

  function d3_layout_treemapPad(node, padding) {
    var x = node.x + padding[3],
        y = node.y + padding[0],
        dx = node.dx - padding[1] - padding[3],
        dy = node.dy - padding[0] - padding[2];

    if (dx < 0) {
      x += dx / 2;
      dx = 0;
    }

    if (dy < 0) {
      y += dy / 2;
      dy = 0;
    }

    return {
      x: x,
      y: y,
      dx: dx,
      dy: dy
    };
  }

  d3.random = {
    normal: function normal(µ, σ) {
      var n = arguments.length;
      if (n < 2) σ = 1;
      if (n < 1) µ = 0;
      return function () {
        var x, y, r;

        do {
          x = Math.random() * 2 - 1;
          y = Math.random() * 2 - 1;
          r = x * x + y * y;
        } while (!r || r > 1);

        return µ + σ * x * Math.sqrt(-2 * Math.log(r) / r);
      };
    },
    logNormal: function logNormal() {
      var random = d3.random.normal.apply(d3, arguments);
      return function () {
        return Math.exp(random());
      };
    },
    irwinHall: function irwinHall(m) {
      return function () {
        for (var s = 0, j = 0; j < m; j++) {
          s += Math.random();
        }

        return s / m;
      };
    }
  };
  d3.scale = {};

  function d3_scaleExtent(domain) {
    var start = domain[0],
        stop = domain[domain.length - 1];
    return start < stop ? [start, stop] : [stop, start];
  }

  function d3_scaleRange(scale) {
    return scale.rangeExtent ? scale.rangeExtent() : d3_scaleExtent(scale.range());
  }

  function d3_scale_bilinear(domain, range, uninterpolate, interpolate) {
    var u = uninterpolate(domain[0], domain[1]),
        i = interpolate(range[0], range[1]);
    return function (x) {
      return i(u(x));
    };
  }

  function d3_scale_nice(domain, nice) {
    var i0 = 0,
        i1 = domain.length - 1,
        x0 = domain[i0],
        x1 = domain[i1],
        dx;

    if (x1 < x0) {
      dx = i0, i0 = i1, i1 = dx;
      dx = x0, x0 = x1, x1 = dx;
    }

    if (nice = nice(x1 - x0)) {
      domain[i0] = nice.floor(x0);
      domain[i1] = nice.ceil(x1);
    }

    return domain;
  }

  function d3_scale_polylinear(domain, range, uninterpolate, interpolate) {
    var u = [],
        i = [],
        j = 0,
        k = Math.min(domain.length, range.length) - 1;

    if (domain[k] < domain[0]) {
      domain = domain.slice().reverse();
      range = range.slice().reverse();
    }

    while (++j <= k) {
      u.push(uninterpolate(domain[j - 1], domain[j]));
      i.push(interpolate(range[j - 1], range[j]));
    }

    return function (x) {
      var j = d3.bisect(domain, x, 1, k) - 1;
      return i[j](u[j](x));
    };
  }

  d3.scale.linear = function () {
    return d3_scale_linear([0, 1], [0, 1], d3_interpolate, false);
  };

  function d3_scale_linear(domain, range, interpolate, clamp) {
    var output, input;

    function rescale() {
      var linear = Math.min(domain.length, range.length) > 2 ? d3_scale_polylinear : d3_scale_bilinear,
          uninterpolate = clamp ? d3_uninterpolateClamp : d3_uninterpolateNumber;
      output = linear(domain, range, uninterpolate, interpolate);
      input = linear(range, domain, uninterpolate, d3_interpolate);
      return scale;
    }

    function scale(x) {
      return output(x);
    }

    scale.invert = function (y) {
      return input(y);
    };

    scale.domain = function (x) {
      if (!arguments.length) return domain;
      domain = x.map(Number);
      return rescale();
    };

    scale.range = function (x) {
      if (!arguments.length) return range;
      range = x;
      return rescale();
    };

    scale.rangeRound = function (x) {
      return scale.range(x).interpolate(d3_interpolateRound);
    };

    scale.clamp = function (x) {
      if (!arguments.length) return clamp;
      clamp = x;
      return rescale();
    };

    scale.interpolate = function (x) {
      if (!arguments.length) return interpolate;
      interpolate = x;
      return rescale();
    };

    scale.ticks = function (m) {
      return d3_scale_linearTicks(domain, m);
    };

    scale.tickFormat = function (m, format) {
      return d3_scale_linearTickFormat(domain, m, format);
    };

    scale.nice = function () {
      d3_scale_nice(domain, d3_scale_linearNice);
      return rescale();
    };

    scale.copy = function () {
      return d3_scale_linear(domain, range, interpolate, clamp);
    };

    return rescale();
  }

  function d3_scale_linearRebind(scale, linear) {
    return d3.rebind(scale, linear, "range", "rangeRound", "interpolate", "clamp");
  }

  function d3_scale_linearNice(dx) {
    dx = Math.pow(10, Math.round(Math.log(dx) / Math.LN10) - 1);
    return dx && {
      floor: function floor(x) {
        return Math.floor(x / dx) * dx;
      },
      ceil: function ceil(x) {
        return Math.ceil(x / dx) * dx;
      }
    };
  }

  function d3_scale_linearTickRange(domain, m) {
    var extent = d3_scaleExtent(domain),
        span = extent[1] - extent[0],
        step = Math.pow(10, Math.floor(Math.log(span / m) / Math.LN10)),
        err = m / span * step;
    if (err <= .15) step *= 10;else if (err <= .35) step *= 5;else if (err <= .75) step *= 2;
    extent[0] = Math.ceil(extent[0] / step) * step;
    extent[1] = Math.floor(extent[1] / step) * step + step * .5;
    extent[2] = step;
    return extent;
  }

  function d3_scale_linearTicks(domain, m) {
    return d3.range.apply(d3, d3_scale_linearTickRange(domain, m));
  }

  function d3_scale_linearTickFormat(domain, m, format) {
    var precision = -Math.floor(Math.log(d3_scale_linearTickRange(domain, m)[2]) / Math.LN10 + .01);
    return d3.format(format ? format.replace(d3_format_re, function (a, b, c, d, e, f, g, h, i, j) {
      return [b, c, d, e, f, g, h, i || "." + (precision - (j === "%") * 2), j].join("");
    }) : ",." + precision + "f");
  }

  d3.scale.log = function () {
    return d3_scale_log(d3.scale.linear().domain([0, Math.LN10]), 10, d3_scale_logp, d3_scale_powp);
  };

  function d3_scale_log(linear, base, log, pow) {
    function scale(x) {
      return linear(log(x));
    }

    scale.invert = function (x) {
      return pow(linear.invert(x));
    };

    scale.domain = function (x) {
      if (!arguments.length) return linear.domain().map(pow);
      if (x[0] < 0) log = d3_scale_logn, pow = d3_scale_pown;else log = d3_scale_logp, pow = d3_scale_powp;
      linear.domain(x.map(log));
      return scale;
    };

    scale.base = function (_) {
      if (!arguments.length) return base;
      base = +_;
      return scale;
    };

    scale.nice = function () {
      linear.domain(d3_scale_nice(linear.domain(), d3_scale_logNice(base)));
      return scale;
    };

    scale.ticks = function () {
      var extent = d3_scaleExtent(linear.domain()),
          ticks = [];

      if (extent.every(isFinite)) {
        var b = Math.log(base),
            i = Math.floor(extent[0] / b),
            j = Math.ceil(extent[1] / b),
            u = pow(extent[0]),
            v = pow(extent[1]),
            n = base % 1 ? 2 : base;

        if (log === d3_scale_logn) {
          ticks.push(-Math.pow(base, -i));

          for (; i++ < j;) {
            for (var k = n - 1; k > 0; k--) {
              ticks.push(-Math.pow(base, -i) * k);
            }
          }
        } else {
          for (; i < j; i++) {
            for (var k = 1; k < n; k++) {
              ticks.push(Math.pow(base, i) * k);
            }
          }

          ticks.push(Math.pow(base, i));
        }

        for (i = 0; ticks[i] < u; i++) {}

        for (j = ticks.length; ticks[j - 1] > v; j--) {}

        ticks = ticks.slice(i, j);
      }

      return ticks;
    };

    scale.tickFormat = function (n, format) {
      if (arguments.length < 2) format = d3_scale_logFormat;
      if (!arguments.length) return format;
      var b = Math.log(base),
          k = Math.max(.1, n / scale.ticks().length),
          f = log === d3_scale_logn ? (e = -1e-12, Math.floor) : (e = 1e-12, Math.ceil),
          e;
      return function (d) {
        return d / pow(b * f(log(d) / b + e)) <= k ? format(d) : "";
      };
    };

    scale.copy = function () {
      return d3_scale_log(linear.copy(), base, log, pow);
    };

    return d3_scale_linearRebind(scale, linear);
  }

  var d3_scale_logFormat = d3.format(".0e");

  function d3_scale_logp(x) {
    return Math.log(x < 0 ? 0 : x);
  }

  function d3_scale_powp(x) {
    return Math.exp(x);
  }

  function d3_scale_logn(x) {
    return -Math.log(x > 0 ? 0 : -x);
  }

  function d3_scale_pown(x) {
    return -Math.exp(-x);
  }

  function d3_scale_logNice(base) {
    base = Math.log(base);
    var nice = {
      floor: function floor(x) {
        return Math.floor(x / base) * base;
      },
      ceil: function ceil(x) {
        return Math.ceil(x / base) * base;
      }
    };
    return function () {
      return nice;
    };
  }

  d3.scale.pow = function () {
    return d3_scale_pow(d3.scale.linear(), 1);
  };

  function d3_scale_pow(linear, exponent) {
    var powp = d3_scale_powPow(exponent),
        powb = d3_scale_powPow(1 / exponent);

    function scale(x) {
      return linear(powp(x));
    }

    scale.invert = function (x) {
      return powb(linear.invert(x));
    };

    scale.domain = function (x) {
      if (!arguments.length) return linear.domain().map(powb);
      linear.domain(x.map(powp));
      return scale;
    };

    scale.ticks = function (m) {
      return d3_scale_linearTicks(scale.domain(), m);
    };

    scale.tickFormat = function (m, format) {
      return d3_scale_linearTickFormat(scale.domain(), m, format);
    };

    scale.nice = function () {
      return scale.domain(d3_scale_nice(scale.domain(), d3_scale_linearNice));
    };

    scale.exponent = function (x) {
      if (!arguments.length) return exponent;
      var domain = scale.domain();
      powp = d3_scale_powPow(exponent = x);
      powb = d3_scale_powPow(1 / exponent);
      return scale.domain(domain);
    };

    scale.copy = function () {
      return d3_scale_pow(linear.copy(), exponent);
    };

    return d3_scale_linearRebind(scale, linear);
  }

  function d3_scale_powPow(e) {
    return function (x) {
      return x < 0 ? -Math.pow(-x, e) : Math.pow(x, e);
    };
  }

  d3.scale.sqrt = function () {
    return d3.scale.pow().exponent(.5);
  };

  d3.scale.ordinal = function () {
    return d3_scale_ordinal([], {
      t: "range",
      a: [[]]
    });
  };

  function d3_scale_ordinal(domain, ranger) {
    var index, range, rangeBand;

    function scale(x) {
      return range[((index.get(x) || index.set(x, domain.push(x))) - 1) % range.length];
    }

    function steps(start, step) {
      return d3.range(domain.length).map(function (i) {
        return start + step * i;
      });
    }

    scale.domain = function (x) {
      if (!arguments.length) return domain;
      domain = [];
      index = new d3_Map();
      var i = -1,
          n = x.length,
          xi;

      while (++i < n) {
        if (!index.has(xi = x[i])) index.set(xi, domain.push(xi));
      }

      return scale[ranger.t].apply(scale, ranger.a);
    };

    scale.range = function (x) {
      if (!arguments.length) return range;
      range = x;
      rangeBand = 0;
      ranger = {
        t: "range",
        a: arguments
      };
      return scale;
    };

    scale.rangePoints = function (x, padding) {
      if (arguments.length < 2) padding = 0;
      var start = x[0],
          stop = x[1],
          step = (stop - start) / (Math.max(1, domain.length - 1) + padding);
      range = steps(domain.length < 2 ? (start + stop) / 2 : start + step * padding / 2, step);
      rangeBand = 0;
      ranger = {
        t: "rangePoints",
        a: arguments
      };
      return scale;
    };

    scale.rangeBands = function (x, padding, outerPadding) {
      if (arguments.length < 2) padding = 0;
      if (arguments.length < 3) outerPadding = padding;
      var reverse = x[1] < x[0],
          start = x[reverse - 0],
          stop = x[1 - reverse],
          step = (stop - start) / (domain.length - padding + 2 * outerPadding);
      range = steps(start + step * outerPadding, step);
      if (reverse) range.reverse();
      rangeBand = step * (1 - padding);
      ranger = {
        t: "rangeBands",
        a: arguments
      };
      return scale;
    };

    scale.rangeRoundBands = function (x, padding, outerPadding) {
      if (arguments.length < 2) padding = 0;
      if (arguments.length < 3) outerPadding = padding;
      var reverse = x[1] < x[0],
          start = x[reverse - 0],
          stop = x[1 - reverse],
          step = Math.floor((stop - start) / (domain.length - padding + 2 * outerPadding)),
          error = stop - start - (domain.length - padding) * step;
      range = steps(start + Math.round(error / 2), step);
      if (reverse) range.reverse();
      rangeBand = Math.round(step * (1 - padding));
      ranger = {
        t: "rangeRoundBands",
        a: arguments
      };
      return scale;
    };

    scale.rangeBand = function () {
      return rangeBand;
    };

    scale.rangeExtent = function () {
      return d3_scaleExtent(ranger.a[0]);
    };

    scale.copy = function () {
      return d3_scale_ordinal(domain, ranger);
    };

    return scale.domain(domain);
  }

  d3.scale.category10 = function () {
    return d3.scale.ordinal().range(d3_category10);
  };

  d3.scale.category20 = function () {
    return d3.scale.ordinal().range(d3_category20);
  };

  d3.scale.category20b = function () {
    return d3.scale.ordinal().range(d3_category20b);
  };

  d3.scale.category20c = function () {
    return d3.scale.ordinal().range(d3_category20c);
  };

  var d3_category10 = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"];
  var d3_category20 = ["#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5"];
  var d3_category20b = ["#393b79", "#5254a3", "#6b6ecf", "#9c9ede", "#637939", "#8ca252", "#b5cf6b", "#cedb9c", "#8c6d31", "#bd9e39", "#e7ba52", "#e7cb94", "#843c39", "#ad494a", "#d6616b", "#e7969c", "#7b4173", "#a55194", "#ce6dbd", "#de9ed6"];
  var d3_category20c = ["#3182bd", "#6baed6", "#9ecae1", "#c6dbef", "#e6550d", "#fd8d3c", "#fdae6b", "#fdd0a2", "#31a354", "#74c476", "#a1d99b", "#c7e9c0", "#756bb1", "#9e9ac8", "#bcbddc", "#dadaeb", "#636363", "#969696", "#bdbdbd", "#d9d9d9"];

  d3.scale.quantile = function () {
    return d3_scale_quantile([], []);
  };

  function d3_scale_quantile(domain, range) {
    var thresholds;

    function rescale() {
      var k = 0,
          q = range.length;
      thresholds = [];

      while (++k < q) {
        thresholds[k - 1] = d3.quantile(domain, k / q);
      }

      return scale;
    }

    function scale(x) {
      if (isNaN(x = +x)) return NaN;
      return range[d3.bisect(thresholds, x)];
    }

    scale.domain = function (x) {
      if (!arguments.length) return domain;
      domain = x.filter(function (d) {
        return !isNaN(d);
      }).sort(d3.ascending);
      return rescale();
    };

    scale.range = function (x) {
      if (!arguments.length) return range;
      range = x;
      return rescale();
    };

    scale.quantiles = function () {
      return thresholds;
    };

    scale.copy = function () {
      return d3_scale_quantile(domain, range);
    };

    return rescale();
  }

  d3.scale.quantize = function () {
    return d3_scale_quantize(0, 1, [0, 1]);
  };

  function d3_scale_quantize(x0, x1, range) {
    var kx, i;

    function scale(x) {
      return range[Math.max(0, Math.min(i, Math.floor(kx * (x - x0))))];
    }

    function rescale() {
      kx = range.length / (x1 - x0);
      i = range.length - 1;
      return scale;
    }

    scale.domain = function (x) {
      if (!arguments.length) return [x0, x1];
      x0 = +x[0];
      x1 = +x[x.length - 1];
      return rescale();
    };

    scale.range = function (x) {
      if (!arguments.length) return range;
      range = x;
      return rescale();
    };

    scale.copy = function () {
      return d3_scale_quantize(x0, x1, range);
    };

    return rescale();
  }

  d3.scale.threshold = function () {
    return d3_scale_threshold([.5], [0, 1]);
  };

  function d3_scale_threshold(domain, range) {
    function scale(x) {
      return range[d3.bisect(domain, x)];
    }

    scale.domain = function (_) {
      if (!arguments.length) return domain;
      domain = _;
      return scale;
    };

    scale.range = function (_) {
      if (!arguments.length) return range;
      range = _;
      return scale;
    };

    scale.copy = function () {
      return d3_scale_threshold(domain, range);
    };

    return scale;
  }

  d3.scale.identity = function () {
    return d3_scale_identity([0, 1]);
  };

  function d3_scale_identity(domain) {
    function identity(x) {
      return +x;
    }

    identity.invert = identity;

    identity.domain = identity.range = function (x) {
      if (!arguments.length) return domain;
      domain = x.map(identity);
      return identity;
    };

    identity.ticks = function (m) {
      return d3_scale_linearTicks(domain, m);
    };

    identity.tickFormat = function (m, format) {
      return d3_scale_linearTickFormat(domain, m, format);
    };

    identity.copy = function () {
      return d3_scale_identity(domain);
    };

    return identity;
  }

  d3.svg.arc = function () {
    var innerRadius = d3_svg_arcInnerRadius,
        outerRadius = d3_svg_arcOuterRadius,
        startAngle = d3_svg_arcStartAngle,
        endAngle = d3_svg_arcEndAngle;

    function arc() {
      var r0 = innerRadius.apply(this, arguments),
          r1 = outerRadius.apply(this, arguments),
          a0 = startAngle.apply(this, arguments) + d3_svg_arcOffset,
          a1 = endAngle.apply(this, arguments) + d3_svg_arcOffset,
          da = (a1 < a0 && (da = a0, a0 = a1, a1 = da), a1 - a0),
          df = da < π ? "0" : "1",
          c0 = Math.cos(a0),
          s0 = Math.sin(a0),
          c1 = Math.cos(a1),
          s1 = Math.sin(a1);
      return da >= d3_svg_arcMax ? r0 ? "M0," + r1 + "A" + r1 + "," + r1 + " 0 1,1 0," + -r1 + "A" + r1 + "," + r1 + " 0 1,1 0," + r1 + "M0," + r0 + "A" + r0 + "," + r0 + " 0 1,0 0," + -r0 + "A" + r0 + "," + r0 + " 0 1,0 0," + r0 + "Z" : "M0," + r1 + "A" + r1 + "," + r1 + " 0 1,1 0," + -r1 + "A" + r1 + "," + r1 + " 0 1,1 0," + r1 + "Z" : r0 ? "M" + r1 * c0 + "," + r1 * s0 + "A" + r1 + "," + r1 + " 0 " + df + ",1 " + r1 * c1 + "," + r1 * s1 + "L" + r0 * c1 + "," + r0 * s1 + "A" + r0 + "," + r0 + " 0 " + df + ",0 " + r0 * c0 + "," + r0 * s0 + "Z" : "M" + r1 * c0 + "," + r1 * s0 + "A" + r1 + "," + r1 + " 0 " + df + ",1 " + r1 * c1 + "," + r1 * s1 + "L0,0" + "Z";
    }

    arc.innerRadius = function (v) {
      if (!arguments.length) return innerRadius;
      innerRadius = d3_functor(v);
      return arc;
    };

    arc.outerRadius = function (v) {
      if (!arguments.length) return outerRadius;
      outerRadius = d3_functor(v);
      return arc;
    };

    arc.startAngle = function (v) {
      if (!arguments.length) return startAngle;
      startAngle = d3_functor(v);
      return arc;
    };

    arc.endAngle = function (v) {
      if (!arguments.length) return endAngle;
      endAngle = d3_functor(v);
      return arc;
    };

    arc.centroid = function () {
      var r = (innerRadius.apply(this, arguments) + outerRadius.apply(this, arguments)) / 2,
          a = (startAngle.apply(this, arguments) + endAngle.apply(this, arguments)) / 2 + d3_svg_arcOffset;
      return [Math.cos(a) * r, Math.sin(a) * r];
    };

    return arc;
  };

  var d3_svg_arcOffset = -π / 2,
      d3_svg_arcMax = 2 * π - 1e-6;

  function d3_svg_arcInnerRadius(d) {
    return d.innerRadius;
  }

  function d3_svg_arcOuterRadius(d) {
    return d.outerRadius;
  }

  function d3_svg_arcStartAngle(d) {
    return d.startAngle;
  }

  function d3_svg_arcEndAngle(d) {
    return d.endAngle;
  }

  d3.svg.line.radial = function () {
    var line = d3_svg_line(d3_svg_lineRadial);
    line.radius = line.x, delete line.x;
    line.angle = line.y, delete line.y;
    return line;
  };

  function d3_svg_lineRadial(points) {
    var point,
        i = -1,
        n = points.length,
        r,
        a;

    while (++i < n) {
      point = points[i];
      r = point[0];
      a = point[1] + d3_svg_arcOffset;
      point[0] = r * Math.cos(a);
      point[1] = r * Math.sin(a);
    }

    return points;
  }

  function d3_svg_area(projection) {
    var x0 = d3_svg_lineX,
        x1 = d3_svg_lineX,
        y0 = 0,
        y1 = d3_svg_lineY,
        defined = d3_true,
        interpolate = d3_svg_lineLinear,
        interpolateKey = interpolate.key,
        interpolateReverse = interpolate,
        L = "L",
        tension = .7;

    function area(data) {
      var segments = [],
          points0 = [],
          points1 = [],
          i = -1,
          n = data.length,
          d,
          fx0 = d3_functor(x0),
          fy0 = d3_functor(y0),
          fx1 = x0 === x1 ? function () {
        return x;
      } : d3_functor(x1),
          fy1 = y0 === y1 ? function () {
        return y;
      } : d3_functor(y1),
          x,
          y;

      function segment() {
        segments.push("M", interpolate(projection(points1), tension), L, interpolateReverse(projection(points0.reverse()), tension), "Z");
      }

      while (++i < n) {
        if (defined.call(this, d = data[i], i)) {
          points0.push([x = +fx0.call(this, d, i), y = +fy0.call(this, d, i)]);
          points1.push([+fx1.call(this, d, i), +fy1.call(this, d, i)]);
        } else if (points0.length) {
          segment();
          points0 = [];
          points1 = [];
        }
      }

      if (points0.length) segment();
      return segments.length ? segments.join("") : null;
    }

    area.x = function (_) {
      if (!arguments.length) return x1;
      x0 = x1 = _;
      return area;
    };

    area.x0 = function (_) {
      if (!arguments.length) return x0;
      x0 = _;
      return area;
    };

    area.x1 = function (_) {
      if (!arguments.length) return x1;
      x1 = _;
      return area;
    };

    area.y = function (_) {
      if (!arguments.length) return y1;
      y0 = y1 = _;
      return area;
    };

    area.y0 = function (_) {
      if (!arguments.length) return y0;
      y0 = _;
      return area;
    };

    area.y1 = function (_) {
      if (!arguments.length) return y1;
      y1 = _;
      return area;
    };

    area.defined = function (_) {
      if (!arguments.length) return defined;
      defined = _;
      return area;
    };

    area.interpolate = function (_) {
      if (!arguments.length) return interpolateKey;
      if (typeof _ === "function") interpolateKey = interpolate = _;else interpolateKey = (interpolate = d3_svg_lineInterpolators.get(_) || d3_svg_lineLinear).key;
      interpolateReverse = interpolate.reverse || interpolate;
      L = interpolate.closed ? "M" : "L";
      return area;
    };

    area.tension = function (_) {
      if (!arguments.length) return tension;
      tension = _;
      return area;
    };

    return area;
  }

  d3_svg_lineStepBefore.reverse = d3_svg_lineStepAfter;
  d3_svg_lineStepAfter.reverse = d3_svg_lineStepBefore;

  d3.svg.area = function () {
    return d3_svg_area(d3_identity);
  };

  d3.svg.area.radial = function () {
    var area = d3_svg_area(d3_svg_lineRadial);
    area.radius = area.x, delete area.x;
    area.innerRadius = area.x0, delete area.x0;
    area.outerRadius = area.x1, delete area.x1;
    area.angle = area.y, delete area.y;
    area.startAngle = area.y0, delete area.y0;
    area.endAngle = area.y1, delete area.y1;
    return area;
  };

  d3.svg.chord = function () {
    var source = d3_source,
        target = d3_target,
        radius = d3_svg_chordRadius,
        startAngle = d3_svg_arcStartAngle,
        endAngle = d3_svg_arcEndAngle;

    function chord(d, i) {
      var s = subgroup(this, source, d, i),
          t = subgroup(this, target, d, i);
      return "M" + s.p0 + arc(s.r, s.p1, s.a1 - s.a0) + (equals(s, t) ? curve(s.r, s.p1, s.r, s.p0) : curve(s.r, s.p1, t.r, t.p0) + arc(t.r, t.p1, t.a1 - t.a0) + curve(t.r, t.p1, s.r, s.p0)) + "Z";
    }

    function subgroup(self, f, d, i) {
      var subgroup = f.call(self, d, i),
          r = radius.call(self, subgroup, i),
          a0 = startAngle.call(self, subgroup, i) + d3_svg_arcOffset,
          a1 = endAngle.call(self, subgroup, i) + d3_svg_arcOffset;
      return {
        r: r,
        a0: a0,
        a1: a1,
        p0: [r * Math.cos(a0), r * Math.sin(a0)],
        p1: [r * Math.cos(a1), r * Math.sin(a1)]
      };
    }

    function equals(a, b) {
      return a.a0 == b.a0 && a.a1 == b.a1;
    }

    function arc(r, p, a) {
      return "A" + r + "," + r + " 0 " + +(a > π) + ",1 " + p;
    }

    function curve(r0, p0, r1, p1) {
      return "Q 0,0 " + p1;
    }

    chord.radius = function (v) {
      if (!arguments.length) return radius;
      radius = d3_functor(v);
      return chord;
    };

    chord.source = function (v) {
      if (!arguments.length) return source;
      source = d3_functor(v);
      return chord;
    };

    chord.target = function (v) {
      if (!arguments.length) return target;
      target = d3_functor(v);
      return chord;
    };

    chord.startAngle = function (v) {
      if (!arguments.length) return startAngle;
      startAngle = d3_functor(v);
      return chord;
    };

    chord.endAngle = function (v) {
      if (!arguments.length) return endAngle;
      endAngle = d3_functor(v);
      return chord;
    };

    return chord;
  };

  function d3_svg_chordRadius(d) {
    return d.radius;
  }

  d3.svg.diagonal = function () {
    var source = d3_source,
        target = d3_target,
        projection = d3_svg_diagonalProjection;

    function diagonal(d, i) {
      var p0 = source.call(this, d, i),
          p3 = target.call(this, d, i),
          m = (p0.y + p3.y) / 2,
          p = [p0, {
        x: p0.x,
        y: m
      }, {
        x: p3.x,
        y: m
      }, p3];
      p = p.map(projection);
      return "M" + p[0] + "C" + p[1] + " " + p[2] + " " + p[3];
    }

    diagonal.source = function (x) {
      if (!arguments.length) return source;
      source = d3_functor(x);
      return diagonal;
    };

    diagonal.target = function (x) {
      if (!arguments.length) return target;
      target = d3_functor(x);
      return diagonal;
    };

    diagonal.projection = function (x) {
      if (!arguments.length) return projection;
      projection = x;
      return diagonal;
    };

    return diagonal;
  };

  function d3_svg_diagonalProjection(d) {
    return [d.x, d.y];
  }

  d3.svg.diagonal.radial = function () {
    var diagonal = d3.svg.diagonal(),
        projection = d3_svg_diagonalProjection,
        projection_ = diagonal.projection;

    diagonal.projection = function (x) {
      return arguments.length ? projection_(d3_svg_diagonalRadialProjection(projection = x)) : projection;
    };

    return diagonal;
  };

  function d3_svg_diagonalRadialProjection(projection) {
    return function () {
      var d = projection.apply(this, arguments),
          r = d[0],
          a = d[1] + d3_svg_arcOffset;
      return [r * Math.cos(a), r * Math.sin(a)];
    };
  }

  d3.svg.symbol = function () {
    var type = d3_svg_symbolType,
        size = d3_svg_symbolSize;

    function symbol(d, i) {
      return (d3_svg_symbols.get(type.call(this, d, i)) || d3_svg_symbolCircle)(size.call(this, d, i));
    }

    symbol.type = function (x) {
      if (!arguments.length) return type;
      type = d3_functor(x);
      return symbol;
    };

    symbol.size = function (x) {
      if (!arguments.length) return size;
      size = d3_functor(x);
      return symbol;
    };

    return symbol;
  };

  function d3_svg_symbolSize() {
    return 64;
  }

  function d3_svg_symbolType() {
    return "circle";
  }

  function d3_svg_symbolCircle(size) {
    var r = Math.sqrt(size / π);
    return "M0," + r + "A" + r + "," + r + " 0 1,1 0," + -r + "A" + r + "," + r + " 0 1,1 0," + r + "Z";
  }

  var d3_svg_symbols = d3.map({
    circle: d3_svg_symbolCircle,
    cross: function cross(size) {
      var r = Math.sqrt(size / 5) / 2;
      return "M" + -3 * r + "," + -r + "H" + -r + "V" + -3 * r + "H" + r + "V" + -r + "H" + 3 * r + "V" + r + "H" + r + "V" + 3 * r + "H" + -r + "V" + r + "H" + -3 * r + "Z";
    },
    diamond: function diamond(size) {
      var ry = Math.sqrt(size / (2 * d3_svg_symbolTan30)),
          rx = ry * d3_svg_symbolTan30;
      return "M0," + -ry + "L" + rx + ",0" + " 0," + ry + " " + -rx + ",0" + "Z";
    },
    square: function square(size) {
      var r = Math.sqrt(size) / 2;
      return "M" + -r + "," + -r + "L" + r + "," + -r + " " + r + "," + r + " " + -r + "," + r + "Z";
    },
    "triangle-down": function triangleDown(size) {
      var rx = Math.sqrt(size / d3_svg_symbolSqrt3),
          ry = rx * d3_svg_symbolSqrt3 / 2;
      return "M0," + ry + "L" + rx + "," + -ry + " " + -rx + "," + -ry + "Z";
    },
    "triangle-up": function triangleUp(size) {
      var rx = Math.sqrt(size / d3_svg_symbolSqrt3),
          ry = rx * d3_svg_symbolSqrt3 / 2;
      return "M0," + -ry + "L" + rx + "," + ry + " " + -rx + "," + ry + "Z";
    }
  });
  d3.svg.symbolTypes = d3_svg_symbols.keys();
  var d3_svg_symbolSqrt3 = Math.sqrt(3),
      d3_svg_symbolTan30 = Math.tan(30 * d3_radians);

  function d3_transition(groups, id) {
    d3_arraySubclass(groups, d3_transitionPrototype);
    groups.id = id;
    return groups;
  }

  var d3_transitionPrototype = [],
      d3_transitionId = 0,
      d3_transitionInheritId,
      d3_transitionInherit = {
    ease: d3_ease_cubicInOut,
    delay: 0,
    duration: 250
  };
  d3_transitionPrototype.call = d3_selectionPrototype.call;
  d3_transitionPrototype.empty = d3_selectionPrototype.empty;
  d3_transitionPrototype.node = d3_selectionPrototype.node;

  d3.transition = function (selection) {
    return arguments.length ? d3_transitionInheritId ? selection.transition() : selection : d3_selectionRoot.transition();
  };

  d3.transition.prototype = d3_transitionPrototype;

  d3_transitionPrototype.select = function (selector) {
    var id = this.id,
        subgroups = [],
        subgroup,
        subnode,
        node;
    if (typeof selector !== "function") selector = d3_selection_selector(selector);

    for (var j = -1, m = this.length; ++j < m;) {
      subgroups.push(subgroup = []);

      for (var group = this[j], i = -1, n = group.length; ++i < n;) {
        if ((node = group[i]) && (subnode = selector.call(node, node.__data__, i))) {
          if ("__data__" in node) subnode.__data__ = node.__data__;
          d3_transitionNode(subnode, i, id, node.__transition__[id]);
          subgroup.push(subnode);
        } else {
          subgroup.push(null);
        }
      }
    }

    return d3_transition(subgroups, id);
  };

  d3_transitionPrototype.selectAll = function (selector) {
    var id = this.id,
        subgroups = [],
        subgroup,
        subnodes,
        node,
        subnode,
        transition;
    if (typeof selector !== "function") selector = d3_selection_selectorAll(selector);

    for (var j = -1, m = this.length; ++j < m;) {
      for (var group = this[j], i = -1, n = group.length; ++i < n;) {
        if (node = group[i]) {
          transition = node.__transition__[id];
          subnodes = selector.call(node, node.__data__, i);
          subgroups.push(subgroup = []);

          for (var k = -1, o = subnodes.length; ++k < o;) {
            d3_transitionNode(subnode = subnodes[k], k, id, transition);
            subgroup.push(subnode);
          }
        }
      }
    }

    return d3_transition(subgroups, id);
  };

  d3_transitionPrototype.filter = function (filter) {
    var subgroups = [],
        subgroup,
        group,
        node;
    if (typeof filter !== "function") filter = d3_selection_filter(filter);

    for (var j = 0, m = this.length; j < m; j++) {
      subgroups.push(subgroup = []);

      for (var group = this[j], i = 0, n = group.length; i < n; i++) {
        if ((node = group[i]) && filter.call(node, node.__data__, i)) {
          subgroup.push(node);
        }
      }
    }

    return d3_transition(subgroups, this.id, this.time).ease(this.ease());
  };

  d3_transitionPrototype.tween = function (name, tween) {
    var id = this.id;
    if (arguments.length < 2) return this.node().__transition__[id].tween.get(name);
    return d3_selection_each(this, tween == null ? function (node) {
      node.__transition__[id].tween.remove(name);
    } : function (node) {
      node.__transition__[id].tween.set(name, tween);
    });
  };

  function d3_transition_tween(groups, name, value, tween) {
    var id = groups.id;
    return d3_selection_each(groups, typeof value === "function" ? function (node, i, j) {
      node.__transition__[id].tween.set(name, tween(value.call(node, node.__data__, i, j)));
    } : (value = tween(value), function (node) {
      node.__transition__[id].tween.set(name, value);
    }));
  }

  d3_transitionPrototype.attr = function (nameNS, value) {
    if (arguments.length < 2) {
      for (value in nameNS) {
        this.attr(value, nameNS[value]);
      }

      return this;
    }

    var interpolate = d3_interpolateByName(nameNS),
        name = d3.ns.qualify(nameNS);

    function attrNull() {
      this.removeAttribute(name);
    }

    function attrNullNS() {
      this.removeAttributeNS(name.space, name.local);
    }

    return d3_transition_tween(this, "attr." + nameNS, value, function (b) {
      function attrString() {
        var a = this.getAttribute(name),
            i;
        return a !== b && (i = interpolate(a, b), function (t) {
          this.setAttribute(name, i(t));
        });
      }

      function attrStringNS() {
        var a = this.getAttributeNS(name.space, name.local),
            i;
        return a !== b && (i = interpolate(a, b), function (t) {
          this.setAttributeNS(name.space, name.local, i(t));
        });
      }

      return b == null ? name.local ? attrNullNS : attrNull : (b += "", name.local ? attrStringNS : attrString);
    });
  };

  d3_transitionPrototype.attrTween = function (nameNS, tween) {
    var name = d3.ns.qualify(nameNS);

    function attrTween(d, i) {
      var f = tween.call(this, d, i, this.getAttribute(name));
      return f && function (t) {
        this.setAttribute(name, f(t));
      };
    }

    function attrTweenNS(d, i) {
      var f = tween.call(this, d, i, this.getAttributeNS(name.space, name.local));
      return f && function (t) {
        this.setAttributeNS(name.space, name.local, f(t));
      };
    }

    return this.tween("attr." + nameNS, name.local ? attrTweenNS : attrTween);
  };

  d3_transitionPrototype.style = function (name, value, priority) {
    var n = arguments.length;

    if (n < 3) {
      if (typeof name !== "string") {
        if (n < 2) value = "";

        for (priority in name) {
          this.style(priority, name[priority], value);
        }

        return this;
      }

      priority = "";
    }

    var interpolate = d3_interpolateByName(name);

    function styleNull() {
      this.style.removeProperty(name);
    }

    return d3_transition_tween(this, "style." + name, value, function (b) {
      function styleString() {
        var a = d3_window.getComputedStyle(this, null).getPropertyValue(name),
            i;
        return a !== b && (i = interpolate(a, b), function (t) {
          this.style.setProperty(name, i(t), priority);
        });
      }

      return b == null ? styleNull : (b += "", styleString);
    });
  };

  d3_transitionPrototype.styleTween = function (name, tween, priority) {
    if (arguments.length < 3) priority = "";
    return this.tween("style." + name, function (d, i) {
      var f = tween.call(this, d, i, d3_window.getComputedStyle(this, null).getPropertyValue(name));
      return f && function (t) {
        this.style.setProperty(name, f(t), priority);
      };
    });
  };

  d3_transitionPrototype.text = function (value) {
    return d3_transition_tween(this, "text", value, d3_transition_text);
  };

  function d3_transition_text(b) {
    if (b == null) b = "";
    return function () {
      this.textContent = b;
    };
  }

  d3_transitionPrototype.remove = function () {
    return this.each("end.transition", function () {
      var p;
      if (!this.__transition__ && (p = this.parentNode)) p.removeChild(this);
    });
  };

  d3_transitionPrototype.ease = function (value) {
    var id = this.id;
    if (arguments.length < 1) return this.node().__transition__[id].ease;
    if (typeof value !== "function") value = d3.ease.apply(d3, arguments);
    return d3_selection_each(this, function (node) {
      node.__transition__[id].ease = value;
    });
  };

  d3_transitionPrototype.delay = function (value) {
    var id = this.id;
    return d3_selection_each(this, typeof value === "function" ? function (node, i, j) {
      node.__transition__[id].delay = value.call(node, node.__data__, i, j) | 0;
    } : (value |= 0, function (node) {
      node.__transition__[id].delay = value;
    }));
  };

  d3_transitionPrototype.duration = function (value) {
    var id = this.id;
    return d3_selection_each(this, typeof value === "function" ? function (node, i, j) {
      node.__transition__[id].duration = Math.max(1, value.call(node, node.__data__, i, j) | 0);
    } : (value = Math.max(1, value | 0), function (node) {
      node.__transition__[id].duration = value;
    }));
  };

  d3_transitionPrototype.each = function (type, listener) {
    var id = this.id;

    if (arguments.length < 2) {
      var inherit = d3_transitionInherit,
          inheritId = d3_transitionInheritId;
      d3_transitionInheritId = id;
      d3_selection_each(this, function (node, i, j) {
        d3_transitionInherit = node.__transition__[id];
        type.call(node, node.__data__, i, j);
      });
      d3_transitionInherit = inherit;
      d3_transitionInheritId = inheritId;
    } else {
      d3_selection_each(this, function (node) {
        node.__transition__[id].event.on(type, listener);
      });
    }

    return this;
  };

  d3_transitionPrototype.transition = function () {
    var id0 = this.id,
        id1 = ++d3_transitionId,
        subgroups = [],
        subgroup,
        group,
        node,
        transition;

    for (var j = 0, m = this.length; j < m; j++) {
      subgroups.push(subgroup = []);

      for (var group = this[j], i = 0, n = group.length; i < n; i++) {
        if (node = group[i]) {
          transition = Object.create(node.__transition__[id0]);
          transition.delay += transition.duration;
          d3_transitionNode(node, i, id1, transition);
        }

        subgroup.push(node);
      }
    }

    return d3_transition(subgroups, id1);
  };

  function d3_transitionNode(node, i, id, inherit) {
    var lock = node.__transition__ || (node.__transition__ = {
      active: 0,
      count: 0
    }),
        transition = lock[id];

    if (!transition) {
      var time = inherit.time;
      transition = lock[id] = {
        tween: new d3_Map(),
        event: d3.dispatch("start", "end"),
        time: time,
        ease: inherit.ease,
        delay: inherit.delay,
        duration: inherit.duration
      };
      ++lock.count;
      d3.timer(function (elapsed) {
        var d = node.__data__,
            ease = transition.ease,
            event = transition.event,
            delay = transition.delay,
            duration = transition.duration,
            tweened = [];
        return delay <= elapsed ? start(elapsed) : d3.timer(start, delay, time), 1;

        function start(elapsed) {
          if (lock.active > id) return stop();
          lock.active = id;
          event.start.call(node, d, i);
          transition.tween.forEach(function (key, value) {
            if (value = value.call(node, d, i)) {
              tweened.push(value);
            }
          });
          if (!tick(elapsed)) d3.timer(tick, 0, time);
          return 1;
        }

        function tick(elapsed) {
          if (lock.active !== id) return stop();
          var t = (elapsed - delay) / duration,
              e = ease(t),
              n = tweened.length;

          while (n > 0) {
            tweened[--n].call(node, e);
          }

          if (t >= 1) {
            stop();
            event.end.call(node, d, i);
            return 1;
          }
        }

        function stop() {
          if (--lock.count) delete lock[id];else delete node.__transition__;
          return 1;
        }
      }, 0, time);
      return transition;
    }
  }

  d3.svg.axis = function () {
    var scale = d3.scale.linear(),
        orient = d3_svg_axisDefaultOrient,
        tickMajorSize = 6,
        tickMinorSize = 6,
        tickEndSize = 6,
        tickPadding = 3,
        tickArguments_ = [10],
        tickValues = null,
        tickFormat_,
        tickSubdivide = 0;

    function axis(g) {
      g.each(function () {
        var g = d3.select(this);
        var ticks = tickValues == null ? scale.ticks ? scale.ticks.apply(scale, tickArguments_) : scale.domain() : tickValues,
            tickFormat = tickFormat_ == null ? scale.tickFormat ? scale.tickFormat.apply(scale, tickArguments_) : String : tickFormat_;
        var subticks = d3_svg_axisSubdivide(scale, ticks, tickSubdivide),
            subtick = g.selectAll(".tick.minor").data(subticks, String),
            subtickEnter = subtick.enter().insert("line", ".tick").attr("class", "tick minor").style("opacity", 1e-6),
            subtickExit = d3.transition(subtick.exit()).style("opacity", 1e-6).remove(),
            subtickUpdate = d3.transition(subtick).style("opacity", 1);
        var tick = g.selectAll(".tick.major").data(ticks, String),
            tickEnter = tick.enter().insert("g", "path").attr("class", "tick major").style("opacity", 1e-6),
            tickExit = d3.transition(tick.exit()).style("opacity", 1e-6).remove(),
            tickUpdate = d3.transition(tick).style("opacity", 1),
            tickTransform;
        var range = d3_scaleRange(scale),
            path = g.selectAll(".domain").data([0]),
            pathUpdate = (path.enter().append("path").attr("class", "domain"), d3.transition(path));
        var scale1 = scale.copy(),
            scale0 = this.__chart__ || scale1;
        this.__chart__ = scale1;
        tickEnter.append("line");
        tickEnter.append("text");
        var lineEnter = tickEnter.select("line"),
            lineUpdate = tickUpdate.select("line"),
            text = tick.select("text").text(tickFormat),
            textEnter = tickEnter.select("text"),
            textUpdate = tickUpdate.select("text");

        switch (orient) {
          case "bottom":
            {
              tickTransform = d3_svg_axisX;
              subtickEnter.attr("y2", tickMinorSize);
              subtickUpdate.attr("x2", 0).attr("y2", tickMinorSize);
              lineEnter.attr("y2", tickMajorSize);
              textEnter.attr("y", Math.max(tickMajorSize, 0) + tickPadding);
              lineUpdate.attr("x2", 0).attr("y2", tickMajorSize);
              textUpdate.attr("x", 0).attr("y", Math.max(tickMajorSize, 0) + tickPadding);
              text.attr("dy", ".71em").style("text-anchor", "middle");
              pathUpdate.attr("d", "M" + range[0] + "," + tickEndSize + "V0H" + range[1] + "V" + tickEndSize);
              break;
            }

          case "top":
            {
              tickTransform = d3_svg_axisX;
              subtickEnter.attr("y2", -tickMinorSize);
              subtickUpdate.attr("x2", 0).attr("y2", -tickMinorSize);
              lineEnter.attr("y2", -tickMajorSize);
              textEnter.attr("y", -(Math.max(tickMajorSize, 0) + tickPadding));
              lineUpdate.attr("x2", 0).attr("y2", -tickMajorSize);
              textUpdate.attr("x", 0).attr("y", -(Math.max(tickMajorSize, 0) + tickPadding));
              text.attr("dy", "0em").style("text-anchor", "middle");
              pathUpdate.attr("d", "M" + range[0] + "," + -tickEndSize + "V0H" + range[1] + "V" + -tickEndSize);
              break;
            }

          case "left":
            {
              tickTransform = d3_svg_axisY;
              subtickEnter.attr("x2", -tickMinorSize);
              subtickUpdate.attr("x2", -tickMinorSize).attr("y2", 0);
              lineEnter.attr("x2", -tickMajorSize);
              textEnter.attr("x", -(Math.max(tickMajorSize, 0) + tickPadding));
              lineUpdate.attr("x2", -tickMajorSize).attr("y2", 0);
              textUpdate.attr("x", -(Math.max(tickMajorSize, 0) + tickPadding)).attr("y", 0);
              text.attr("dy", ".32em").style("text-anchor", "end");
              pathUpdate.attr("d", "M" + -tickEndSize + "," + range[0] + "H0V" + range[1] + "H" + -tickEndSize);
              break;
            }

          case "right":
            {
              tickTransform = d3_svg_axisY;
              subtickEnter.attr("x2", tickMinorSize);
              subtickUpdate.attr("x2", tickMinorSize).attr("y2", 0);
              lineEnter.attr("x2", tickMajorSize);
              textEnter.attr("x", Math.max(tickMajorSize, 0) + tickPadding);
              lineUpdate.attr("x2", tickMajorSize).attr("y2", 0);
              textUpdate.attr("x", Math.max(tickMajorSize, 0) + tickPadding).attr("y", 0);
              text.attr("dy", ".32em").style("text-anchor", "start");
              pathUpdate.attr("d", "M" + tickEndSize + "," + range[0] + "H0V" + range[1] + "H" + tickEndSize);
              break;
            }
        }

        if (scale.ticks) {
          tickEnter.call(tickTransform, scale0);
          tickUpdate.call(tickTransform, scale1);
          tickExit.call(tickTransform, scale1);
          subtickEnter.call(tickTransform, scale0);
          subtickUpdate.call(tickTransform, scale1);
          subtickExit.call(tickTransform, scale1);
        } else {
          var dx = scale1.rangeBand() / 2,
              x = function x(d) {
            return scale1(d) + dx;
          };

          tickEnter.call(tickTransform, x);
          tickUpdate.call(tickTransform, x);
        }
      });
    }

    axis.scale = function (x) {
      if (!arguments.length) return scale;
      scale = x;
      return axis;
    };

    axis.orient = function (x) {
      if (!arguments.length) return orient;
      orient = x in d3_svg_axisOrients ? x + "" : d3_svg_axisDefaultOrient;
      return axis;
    };

    axis.ticks = function () {
      if (!arguments.length) return tickArguments_;
      tickArguments_ = arguments;
      return axis;
    };

    axis.tickValues = function (x) {
      if (!arguments.length) return tickValues;
      tickValues = x;
      return axis;
    };

    axis.tickFormat = function (x) {
      if (!arguments.length) return tickFormat_;
      tickFormat_ = x;
      return axis;
    };

    axis.tickSize = function (x, y) {
      if (!arguments.length) return tickMajorSize;
      var n = arguments.length - 1;
      tickMajorSize = +x;
      tickMinorSize = n > 1 ? +y : tickMajorSize;
      tickEndSize = n > 0 ? +arguments[n] : tickMajorSize;
      return axis;
    };

    axis.tickPadding = function (x) {
      if (!arguments.length) return tickPadding;
      tickPadding = +x;
      return axis;
    };

    axis.tickSubdivide = function (x) {
      if (!arguments.length) return tickSubdivide;
      tickSubdivide = +x;
      return axis;
    };

    return axis;
  };

  var d3_svg_axisDefaultOrient = "bottom",
      d3_svg_axisOrients = {
    top: 1,
    right: 1,
    bottom: 1,
    left: 1
  };

  function d3_svg_axisX(selection, x) {
    selection.attr("transform", function (d) {
      return "translate(" + x(d) + ",0)";
    });
  }

  function d3_svg_axisY(selection, y) {
    selection.attr("transform", function (d) {
      return "translate(0," + y(d) + ")";
    });
  }

  function d3_svg_axisSubdivide(scale, ticks, m) {
    subticks = [];

    if (m && ticks.length > 1) {
      var extent = d3_scaleExtent(scale.domain()),
          subticks,
          i = -1,
          n = ticks.length,
          d = (ticks[1] - ticks[0]) / ++m,
          j,
          v;

      while (++i < n) {
        for (j = m; --j > 0;) {
          if ((v = +ticks[i] - j * d) >= extent[0]) {
            subticks.push(v);
          }
        }
      }

      for (--i, j = 0; ++j < m && (v = +ticks[i] + j * d) < extent[1];) {
        subticks.push(v);
      }
    }

    return subticks;
  }

  d3.svg.brush = function () {
    var event = d3_eventDispatch(brush, "brushstart", "brush", "brushend"),
        x = null,
        y = null,
        resizes = d3_svg_brushResizes[0],
        extent = [[0, 0], [0, 0]],
        extentDomain;

    function brush(g) {
      g.each(function () {
        var g = d3.select(this),
            bg = g.selectAll(".background").data([0]),
            fg = g.selectAll(".extent").data([0]),
            tz = g.selectAll(".resize").data(resizes, String),
            e;
        g.style("pointer-events", "all").on("mousedown.brush", brushstart).on("touchstart.brush", brushstart);
        bg.enter().append("rect").attr("class", "background").style("visibility", "hidden").style("cursor", "crosshair");
        fg.enter().append("rect").attr("class", "extent").style("cursor", "move");
        tz.enter().append("g").attr("class", function (d) {
          return "resize " + d;
        }).style("cursor", function (d) {
          return d3_svg_brushCursor[d];
        }).append("rect").attr("x", function (d) {
          return /[ew]$/.test(d) ? -3 : null;
        }).attr("y", function (d) {
          return /^[ns]/.test(d) ? -3 : null;
        }).attr("width", 6).attr("height", 6).style("visibility", "hidden");
        tz.style("display", brush.empty() ? "none" : null);
        tz.exit().remove();

        if (x) {
          e = d3_scaleRange(x);
          bg.attr("x", e[0]).attr("width", e[1] - e[0]);
          redrawX(g);
        }

        if (y) {
          e = d3_scaleRange(y);
          bg.attr("y", e[0]).attr("height", e[1] - e[0]);
          redrawY(g);
        }

        redraw(g);
      });
    }

    function redraw(g) {
      g.selectAll(".resize").attr("transform", function (d) {
        return "translate(" + extent[+/e$/.test(d)][0] + "," + extent[+/^s/.test(d)][1] + ")";
      });
    }

    function redrawX(g) {
      g.select(".extent").attr("x", extent[0][0]);
      g.selectAll(".extent,.n>rect,.s>rect").attr("width", extent[1][0] - extent[0][0]);
    }

    function redrawY(g) {
      g.select(".extent").attr("y", extent[0][1]);
      g.selectAll(".extent,.e>rect,.w>rect").attr("height", extent[1][1] - extent[0][1]);
    }

    function brushstart() {
      var target = this,
          eventTarget = d3.select(d3.event.target),
          event_ = event.of(target, arguments),
          g = d3.select(target),
          resizing = eventTarget.datum(),
          resizingX = !/^(n|s)$/.test(resizing) && x,
          resizingY = !/^(e|w)$/.test(resizing) && y,
          dragging = eventTarget.classed("extent"),
          center,
          origin = mouse(),
          offset;
      var w = d3.select(d3_window).on("mousemove.brush", brushmove).on("mouseup.brush", brushend).on("touchmove.brush", brushmove).on("touchend.brush", brushend).on("keydown.brush", keydown).on("keyup.brush", keyup);

      if (dragging) {
        origin[0] = extent[0][0] - origin[0];
        origin[1] = extent[0][1] - origin[1];
      } else if (resizing) {
        var ex = +/w$/.test(resizing),
            ey = +/^n/.test(resizing);
        offset = [extent[1 - ex][0] - origin[0], extent[1 - ey][1] - origin[1]];
        origin[0] = extent[ex][0];
        origin[1] = extent[ey][1];
      } else if (d3.event.altKey) center = origin.slice();

      g.style("pointer-events", "none").selectAll(".resize").style("display", null);
      d3.select("body").style("cursor", eventTarget.style("cursor"));
      event_({
        type: "brushstart"
      });
      brushmove();
      d3_eventCancel();

      function mouse() {
        var touches = d3.event.changedTouches;
        return touches ? d3.touches(target, touches)[0] : d3.mouse(target);
      }

      function keydown() {
        if (d3.event.keyCode == 32) {
          if (!dragging) {
            center = null;
            origin[0] -= extent[1][0];
            origin[1] -= extent[1][1];
            dragging = 2;
          }

          d3_eventCancel();
        }
      }

      function keyup() {
        if (d3.event.keyCode == 32 && dragging == 2) {
          origin[0] += extent[1][0];
          origin[1] += extent[1][1];
          dragging = 0;
          d3_eventCancel();
        }
      }

      function brushmove() {
        var point = mouse(),
            moved = false;

        if (offset) {
          point[0] += offset[0];
          point[1] += offset[1];
        }

        if (!dragging) {
          if (d3.event.altKey) {
            if (!center) center = [(extent[0][0] + extent[1][0]) / 2, (extent[0][1] + extent[1][1]) / 2];
            origin[0] = extent[+(point[0] < center[0])][0];
            origin[1] = extent[+(point[1] < center[1])][1];
          } else center = null;
        }

        if (resizingX && move1(point, x, 0)) {
          redrawX(g);
          moved = true;
        }

        if (resizingY && move1(point, y, 1)) {
          redrawY(g);
          moved = true;
        }

        if (moved) {
          redraw(g);
          event_({
            type: "brush",
            mode: dragging ? "move" : "resize"
          });
        }
      }

      function move1(point, scale, i) {
        var range = d3_scaleRange(scale),
            r0 = range[0],
            r1 = range[1],
            position = origin[i],
            size = extent[1][i] - extent[0][i],
            min,
            max;

        if (dragging) {
          r0 -= position;
          r1 -= size + position;
        }

        min = Math.max(r0, Math.min(r1, point[i]));

        if (dragging) {
          max = (min += position) + size;
        } else {
          if (center) position = Math.max(r0, Math.min(r1, 2 * center[i] - min));

          if (position < min) {
            max = min;
            min = position;
          } else {
            max = position;
          }
        }

        if (extent[0][i] !== min || extent[1][i] !== max) {
          extentDomain = null;
          extent[0][i] = min;
          extent[1][i] = max;
          return true;
        }
      }

      function brushend() {
        brushmove();
        g.style("pointer-events", "all").selectAll(".resize").style("display", brush.empty() ? "none" : null);
        d3.select("body").style("cursor", null);
        w.on("mousemove.brush", null).on("mouseup.brush", null).on("touchmove.brush", null).on("touchend.brush", null).on("keydown.brush", null).on("keyup.brush", null);
        event_({
          type: "brushend"
        });
        d3_eventCancel();
      }
    }

    brush.x = function (z) {
      if (!arguments.length) return x;
      x = z;
      resizes = d3_svg_brushResizes[!x << 1 | !y];
      return brush;
    };

    brush.y = function (z) {
      if (!arguments.length) return y;
      y = z;
      resizes = d3_svg_brushResizes[!x << 1 | !y];
      return brush;
    };

    brush.extent = function (z) {
      var x0, x1, y0, y1, t;

      if (!arguments.length) {
        z = extentDomain || extent;

        if (x) {
          x0 = z[0][0], x1 = z[1][0];

          if (!extentDomain) {
            x0 = extent[0][0], x1 = extent[1][0];
            if (x.invert) x0 = x.invert(x0), x1 = x.invert(x1);
            if (x1 < x0) t = x0, x0 = x1, x1 = t;
          }
        }

        if (y) {
          y0 = z[0][1], y1 = z[1][1];

          if (!extentDomain) {
            y0 = extent[0][1], y1 = extent[1][1];
            if (y.invert) y0 = y.invert(y0), y1 = y.invert(y1);
            if (y1 < y0) t = y0, y0 = y1, y1 = t;
          }
        }

        return x && y ? [[x0, y0], [x1, y1]] : x ? [x0, x1] : y && [y0, y1];
      }

      extentDomain = [[0, 0], [0, 0]];

      if (x) {
        x0 = z[0], x1 = z[1];
        if (y) x0 = x0[0], x1 = x1[0];
        extentDomain[0][0] = x0, extentDomain[1][0] = x1;
        if (x.invert) x0 = x(x0), x1 = x(x1);
        if (x1 < x0) t = x0, x0 = x1, x1 = t;
        extent[0][0] = x0 | 0, extent[1][0] = x1 | 0;
      }

      if (y) {
        y0 = z[0], y1 = z[1];
        if (x) y0 = y0[1], y1 = y1[1];
        extentDomain[0][1] = y0, extentDomain[1][1] = y1;
        if (y.invert) y0 = y(y0), y1 = y(y1);
        if (y1 < y0) t = y0, y0 = y1, y1 = t;
        extent[0][1] = y0 | 0, extent[1][1] = y1 | 0;
      }

      return brush;
    };

    brush.clear = function () {
      extentDomain = null;
      extent[0][0] = extent[0][1] = extent[1][0] = extent[1][1] = 0;
      return brush;
    };

    brush.empty = function () {
      return x && extent[0][0] === extent[1][0] || y && extent[0][1] === extent[1][1];
    };

    return d3.rebind(brush, event, "on");
  };

  var d3_svg_brushCursor = {
    n: "ns-resize",
    e: "ew-resize",
    s: "ns-resize",
    w: "ew-resize",
    nw: "nwse-resize",
    ne: "nesw-resize",
    se: "nwse-resize",
    sw: "nesw-resize"
  };
  var d3_svg_brushResizes = [["n", "e", "s", "w", "nw", "ne", "se", "sw"], ["e", "w"], ["n", "s"], []];
  d3.time = {};
  var d3_time = Date,
      d3_time_daySymbols = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  function d3_time_utc() {
    this._ = new Date(arguments.length > 1 ? Date.UTC.apply(this, arguments) : arguments[0]);
  }

  d3_time_utc.prototype = {
    getDate: function getDate() {
      return this._.getUTCDate();
    },
    getDay: function getDay() {
      return this._.getUTCDay();
    },
    getFullYear: function getFullYear() {
      return this._.getUTCFullYear();
    },
    getHours: function getHours() {
      return this._.getUTCHours();
    },
    getMilliseconds: function getMilliseconds() {
      return this._.getUTCMilliseconds();
    },
    getMinutes: function getMinutes() {
      return this._.getUTCMinutes();
    },
    getMonth: function getMonth() {
      return this._.getUTCMonth();
    },
    getSeconds: function getSeconds() {
      return this._.getUTCSeconds();
    },
    getTime: function getTime() {
      return this._.getTime();
    },
    getTimezoneOffset: function getTimezoneOffset() {
      return 0;
    },
    valueOf: function valueOf() {
      return this._.valueOf();
    },
    setDate: function setDate() {
      d3_time_prototype.setUTCDate.apply(this._, arguments);
    },
    setDay: function setDay() {
      d3_time_prototype.setUTCDay.apply(this._, arguments);
    },
    setFullYear: function setFullYear() {
      d3_time_prototype.setUTCFullYear.apply(this._, arguments);
    },
    setHours: function setHours() {
      d3_time_prototype.setUTCHours.apply(this._, arguments);
    },
    setMilliseconds: function setMilliseconds() {
      d3_time_prototype.setUTCMilliseconds.apply(this._, arguments);
    },
    setMinutes: function setMinutes() {
      d3_time_prototype.setUTCMinutes.apply(this._, arguments);
    },
    setMonth: function setMonth() {
      d3_time_prototype.setUTCMonth.apply(this._, arguments);
    },
    setSeconds: function setSeconds() {
      d3_time_prototype.setUTCSeconds.apply(this._, arguments);
    },
    setTime: function setTime() {
      d3_time_prototype.setTime.apply(this._, arguments);
    }
  };
  var d3_time_prototype = Date.prototype;
  var d3_time_formatDateTime = "%a %b %e %X %Y",
      d3_time_formatDate = "%m/%d/%Y",
      d3_time_formatTime = "%H:%M:%S";
  var d3_time_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
      d3_time_dayAbbreviations = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
      d3_time_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
      d3_time_monthAbbreviations = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function d3_time_interval(local, step, number) {
    function round(date) {
      var d0 = local(date),
          d1 = offset(d0, 1);
      return date - d0 < d1 - date ? d0 : d1;
    }

    function ceil(date) {
      step(date = local(new d3_time(date - 1)), 1);
      return date;
    }

    function offset(date, k) {
      step(date = new d3_time(+date), k);
      return date;
    }

    function range(t0, t1, dt) {
      var time = ceil(t0),
          times = [];

      if (dt > 1) {
        while (time < t1) {
          if (!(number(time) % dt)) times.push(new Date(+time));
          step(time, 1);
        }
      } else {
        while (time < t1) {
          times.push(new Date(+time)), step(time, 1);
        }
      }

      return times;
    }

    function range_utc(t0, t1, dt) {
      try {
        d3_time = d3_time_utc;
        var utc = new d3_time_utc();
        utc._ = t0;
        return range(utc, t1, dt);
      } finally {
        d3_time = Date;
      }
    }

    local.floor = local;
    local.round = round;
    local.ceil = ceil;
    local.offset = offset;
    local.range = range;
    var utc = local.utc = d3_time_interval_utc(local);
    utc.floor = utc;
    utc.round = d3_time_interval_utc(round);
    utc.ceil = d3_time_interval_utc(ceil);
    utc.offset = d3_time_interval_utc(offset);
    utc.range = range_utc;
    return local;
  }

  function d3_time_interval_utc(method) {
    return function (date, k) {
      try {
        d3_time = d3_time_utc;
        var utc = new d3_time_utc();
        utc._ = date;
        return method(utc, k)._;
      } finally {
        d3_time = Date;
      }
    };
  }

  d3.time.year = d3_time_interval(function (date) {
    date = d3.time.day(date);
    date.setMonth(0, 1);
    return date;
  }, function (date, offset) {
    date.setFullYear(date.getFullYear() + offset);
  }, function (date) {
    return date.getFullYear();
  });
  d3.time.years = d3.time.year.range;
  d3.time.years.utc = d3.time.year.utc.range;
  d3.time.day = d3_time_interval(function (date) {
    var day = new d3_time(1970, 0);
    day.setFullYear(date.getFullYear(), date.getMonth(), date.getDate());
    return day;
  }, function (date, offset) {
    date.setDate(date.getDate() + offset);
  }, function (date) {
    return date.getDate() - 1;
  });
  d3.time.days = d3.time.day.range;
  d3.time.days.utc = d3.time.day.utc.range;

  d3.time.dayOfYear = function (date) {
    var year = d3.time.year(date);
    return Math.floor((date - year - (date.getTimezoneOffset() - year.getTimezoneOffset()) * 6e4) / 864e5);
  };

  d3_time_daySymbols.forEach(function (day, i) {
    day = day.toLowerCase();
    i = 7 - i;
    var interval = d3.time[day] = d3_time_interval(function (date) {
      (date = d3.time.day(date)).setDate(date.getDate() - (date.getDay() + i) % 7);
      return date;
    }, function (date, offset) {
      date.setDate(date.getDate() + Math.floor(offset) * 7);
    }, function (date) {
      var day = d3.time.year(date).getDay();
      return Math.floor((d3.time.dayOfYear(date) + (day + i) % 7) / 7) - (day !== i);
    });
    d3.time[day + "s"] = interval.range;
    d3.time[day + "s"].utc = interval.utc.range;

    d3.time[day + "OfYear"] = function (date) {
      var day = d3.time.year(date).getDay();
      return Math.floor((d3.time.dayOfYear(date) + (day + i) % 7) / 7);
    };
  });
  d3.time.week = d3.time.sunday;
  d3.time.weeks = d3.time.sunday.range;
  d3.time.weeks.utc = d3.time.sunday.utc.range;
  d3.time.weekOfYear = d3.time.sundayOfYear;

  d3.time.format = function (template) {
    var n = template.length;

    function format(date) {
      var string = [],
          i = -1,
          j = 0,
          c,
          p,
          f;

      while (++i < n) {
        if (template.charCodeAt(i) === 37) {
          string.push(template.substring(j, i));
          if ((p = d3_time_formatPads[c = template.charAt(++i)]) != null) c = template.charAt(++i);
          if (f = d3_time_formats[c]) c = f(date, p == null ? c === "e" ? " " : "0" : p);
          string.push(c);
          j = i + 1;
        }
      }

      string.push(template.substring(j, i));
      return string.join("");
    }

    format.parse = function (string) {
      var d = {
        y: 1900,
        m: 0,
        d: 1,
        H: 0,
        M: 0,
        S: 0,
        L: 0
      },
          i = d3_time_parse(d, template, string, 0);
      if (i != string.length) return null;
      if ("p" in d) d.H = d.H % 12 + d.p * 12;
      var date = new d3_time();
      date.setFullYear(d.y, d.m, d.d);
      date.setHours(d.H, d.M, d.S, d.L);
      return date;
    };

    format.toString = function () {
      return template;
    };

    return format;
  };

  function d3_time_parse(date, template, string, j) {
    var c,
        p,
        i = 0,
        n = template.length,
        m = string.length;

    while (i < n) {
      if (j >= m) return -1;
      c = template.charCodeAt(i++);

      if (c === 37) {
        p = d3_time_parsers[template.charAt(i++)];
        if (!p || (j = p(date, string, j)) < 0) return -1;
      } else if (c != string.charCodeAt(j++)) {
        return -1;
      }
    }

    return j;
  }

  function d3_time_formatRe(names) {
    return new RegExp("^(?:" + names.map(d3.requote).join("|") + ")", "i");
  }

  function d3_time_formatLookup(names) {
    var map = new d3_Map(),
        i = -1,
        n = names.length;

    while (++i < n) {
      map.set(names[i].toLowerCase(), i);
    }

    return map;
  }

  function d3_time_formatPad(value, fill, width) {
    value += "";
    var length = value.length;
    return length < width ? new Array(width - length + 1).join(fill) + value : value;
  }

  var d3_time_dayRe = d3_time_formatRe(d3_time_days),
      d3_time_dayAbbrevRe = d3_time_formatRe(d3_time_dayAbbreviations),
      d3_time_monthRe = d3_time_formatRe(d3_time_months),
      d3_time_monthLookup = d3_time_formatLookup(d3_time_months),
      d3_time_monthAbbrevRe = d3_time_formatRe(d3_time_monthAbbreviations),
      d3_time_monthAbbrevLookup = d3_time_formatLookup(d3_time_monthAbbreviations);
  var d3_time_formatPads = {
    "-": "",
    _: " ",
    "0": "0"
  };
  var d3_time_formats = {
    a: function a(d) {
      return d3_time_dayAbbreviations[d.getDay()];
    },
    A: function A(d) {
      return d3_time_days[d.getDay()];
    },
    b: function b(d) {
      return d3_time_monthAbbreviations[d.getMonth()];
    },
    B: function B(d) {
      return d3_time_months[d.getMonth()];
    },
    c: d3.time.format(d3_time_formatDateTime),
    d: function d(_d, p) {
      return d3_time_formatPad(_d.getDate(), p, 2);
    },
    e: function e(d, p) {
      return d3_time_formatPad(d.getDate(), p, 2);
    },
    H: function H(d, p) {
      return d3_time_formatPad(d.getHours(), p, 2);
    },
    I: function I(d, p) {
      return d3_time_formatPad(d.getHours() % 12 || 12, p, 2);
    },
    j: function j(d, p) {
      return d3_time_formatPad(1 + d3.time.dayOfYear(d), p, 3);
    },
    L: function L(d, p) {
      return d3_time_formatPad(d.getMilliseconds(), p, 3);
    },
    m: function m(d, p) {
      return d3_time_formatPad(d.getMonth() + 1, p, 2);
    },
    M: function M(d, p) {
      return d3_time_formatPad(d.getMinutes(), p, 2);
    },
    p: function p(d) {
      return d.getHours() >= 12 ? "PM" : "AM";
    },
    S: function S(d, p) {
      return d3_time_formatPad(d.getSeconds(), p, 2);
    },
    U: function U(d, p) {
      return d3_time_formatPad(d3.time.sundayOfYear(d), p, 2);
    },
    w: function w(d) {
      return d.getDay();
    },
    W: function W(d, p) {
      return d3_time_formatPad(d3.time.mondayOfYear(d), p, 2);
    },
    x: d3.time.format(d3_time_formatDate),
    X: d3.time.format(d3_time_formatTime),
    y: function y(d, p) {
      return d3_time_formatPad(d.getFullYear() % 100, p, 2);
    },
    Y: function Y(d, p) {
      return d3_time_formatPad(d.getFullYear() % 1e4, p, 4);
    },
    Z: d3_time_zone,
    "%": function _() {
      return "%";
    }
  };
  var d3_time_parsers = {
    a: d3_time_parseWeekdayAbbrev,
    A: d3_time_parseWeekday,
    b: d3_time_parseMonthAbbrev,
    B: d3_time_parseMonth,
    c: d3_time_parseLocaleFull,
    d: d3_time_parseDay,
    e: d3_time_parseDay,
    H: d3_time_parseHour24,
    I: d3_time_parseHour24,
    L: d3_time_parseMilliseconds,
    m: d3_time_parseMonthNumber,
    M: d3_time_parseMinutes,
    p: d3_time_parseAmPm,
    S: d3_time_parseSeconds,
    x: d3_time_parseLocaleDate,
    X: d3_time_parseLocaleTime,
    y: d3_time_parseYear,
    Y: d3_time_parseFullYear
  };

  function d3_time_parseWeekdayAbbrev(date, string, i) {
    d3_time_dayAbbrevRe.lastIndex = 0;
    var n = d3_time_dayAbbrevRe.exec(string.substring(i));
    return n ? i += n[0].length : -1;
  }

  function d3_time_parseWeekday(date, string, i) {
    d3_time_dayRe.lastIndex = 0;
    var n = d3_time_dayRe.exec(string.substring(i));
    return n ? i += n[0].length : -1;
  }

  function d3_time_parseMonthAbbrev(date, string, i) {
    d3_time_monthAbbrevRe.lastIndex = 0;
    var n = d3_time_monthAbbrevRe.exec(string.substring(i));
    return n ? (date.m = d3_time_monthAbbrevLookup.get(n[0].toLowerCase()), i += n[0].length) : -1;
  }

  function d3_time_parseMonth(date, string, i) {
    d3_time_monthRe.lastIndex = 0;
    var n = d3_time_monthRe.exec(string.substring(i));
    return n ? (date.m = d3_time_monthLookup.get(n[0].toLowerCase()), i += n[0].length) : -1;
  }

  function d3_time_parseLocaleFull(date, string, i) {
    return d3_time_parse(date, d3_time_formats.c.toString(), string, i);
  }

  function d3_time_parseLocaleDate(date, string, i) {
    return d3_time_parse(date, d3_time_formats.x.toString(), string, i);
  }

  function d3_time_parseLocaleTime(date, string, i) {
    return d3_time_parse(date, d3_time_formats.X.toString(), string, i);
  }

  function d3_time_parseFullYear(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 4));
    return n ? (date.y = +n[0], i += n[0].length) : -1;
  }

  function d3_time_parseYear(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 2));
    return n ? (date.y = d3_time_expandYear(+n[0]), i += n[0].length) : -1;
  }

  function d3_time_expandYear(d) {
    return d + (d > 68 ? 1900 : 2e3);
  }

  function d3_time_parseMonthNumber(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 2));
    return n ? (date.m = n[0] - 1, i += n[0].length) : -1;
  }

  function d3_time_parseDay(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 2));
    return n ? (date.d = +n[0], i += n[0].length) : -1;
  }

  function d3_time_parseHour24(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 2));
    return n ? (date.H = +n[0], i += n[0].length) : -1;
  }

  function d3_time_parseMinutes(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 2));
    return n ? (date.M = +n[0], i += n[0].length) : -1;
  }

  function d3_time_parseSeconds(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 2));
    return n ? (date.S = +n[0], i += n[0].length) : -1;
  }

  function d3_time_parseMilliseconds(date, string, i) {
    d3_time_numberRe.lastIndex = 0;
    var n = d3_time_numberRe.exec(string.substring(i, i + 3));
    return n ? (date.L = +n[0], i += n[0].length) : -1;
  }

  var d3_time_numberRe = /^\s*\d+/;

  function d3_time_parseAmPm(date, string, i) {
    var n = d3_time_amPmLookup.get(string.substring(i, i += 2).toLowerCase());
    return n == null ? -1 : (date.p = n, i);
  }

  var d3_time_amPmLookup = d3.map({
    am: 0,
    pm: 1
  });

  function d3_time_zone(d) {
    var z = d.getTimezoneOffset(),
        zs = z > 0 ? "-" : "+",
        zh = ~~(Math.abs(z) / 60),
        zm = Math.abs(z) % 60;
    return zs + d3_time_formatPad(zh, "0", 2) + d3_time_formatPad(zm, "0", 2);
  }

  d3.time.format.utc = function (template) {
    var local = d3.time.format(template);

    function format(date) {
      try {
        d3_time = d3_time_utc;
        var utc = new d3_time();
        utc._ = date;
        return local(utc);
      } finally {
        d3_time = Date;
      }
    }

    format.parse = function (string) {
      try {
        d3_time = d3_time_utc;
        var date = local.parse(string);
        return date && date._;
      } finally {
        d3_time = Date;
      }
    };

    format.toString = local.toString;
    return format;
  };

  var d3_time_formatIso = d3.time.format.utc("%Y-%m-%dT%H:%M:%S.%LZ");
  d3.time.format.iso = Date.prototype.toISOString && +new Date("2000-01-01T00:00:00.000Z") ? d3_time_formatIsoNative : d3_time_formatIso;

  function d3_time_formatIsoNative(date) {
    return date.toISOString();
  }

  d3_time_formatIsoNative.parse = function (string) {
    var date = new Date(string);
    return isNaN(date) ? null : date;
  };

  d3_time_formatIsoNative.toString = d3_time_formatIso.toString;
  d3.time.second = d3_time_interval(function (date) {
    return new d3_time(Math.floor(date / 1e3) * 1e3);
  }, function (date, offset) {
    date.setTime(date.getTime() + Math.floor(offset) * 1e3);
  }, function (date) {
    return date.getSeconds();
  });
  d3.time.seconds = d3.time.second.range;
  d3.time.seconds.utc = d3.time.second.utc.range;
  d3.time.minute = d3_time_interval(function (date) {
    return new d3_time(Math.floor(date / 6e4) * 6e4);
  }, function (date, offset) {
    date.setTime(date.getTime() + Math.floor(offset) * 6e4);
  }, function (date) {
    return date.getMinutes();
  });
  d3.time.minutes = d3.time.minute.range;
  d3.time.minutes.utc = d3.time.minute.utc.range;
  d3.time.hour = d3_time_interval(function (date) {
    var timezone = date.getTimezoneOffset() / 60;
    return new d3_time((Math.floor(date / 36e5 - timezone) + timezone) * 36e5);
  }, function (date, offset) {
    date.setTime(date.getTime() + Math.floor(offset) * 36e5);
  }, function (date) {
    return date.getHours();
  });
  d3.time.hours = d3.time.hour.range;
  d3.time.hours.utc = d3.time.hour.utc.range;
  d3.time.month = d3_time_interval(function (date) {
    date = d3.time.day(date);
    date.setDate(1);
    return date;
  }, function (date, offset) {
    date.setMonth(date.getMonth() + offset);
  }, function (date) {
    return date.getMonth();
  });
  d3.time.months = d3.time.month.range;
  d3.time.months.utc = d3.time.month.utc.range;

  function d3_time_scale(linear, methods, format) {
    function scale(x) {
      return linear(x);
    }

    scale.invert = function (x) {
      return d3_time_scaleDate(linear.invert(x));
    };

    scale.domain = function (x) {
      if (!arguments.length) return linear.domain().map(d3_time_scaleDate);
      linear.domain(x);
      return scale;
    };

    scale.nice = function (m) {
      return scale.domain(d3_scale_nice(scale.domain(), function () {
        return m;
      }));
    };

    scale.ticks = function (m, k) {
      var extent = d3_time_scaleExtent(scale.domain());

      if (typeof m !== "function") {
        var span = extent[1] - extent[0],
            target = span / m,
            i = d3.bisect(d3_time_scaleSteps, target);
        if (i == d3_time_scaleSteps.length) return methods.year(extent, m);
        if (!i) return linear.ticks(m).map(d3_time_scaleDate);
        if (Math.log(target / d3_time_scaleSteps[i - 1]) < Math.log(d3_time_scaleSteps[i] / target)) --i;
        m = methods[i];
        k = m[1];
        m = m[0].range;
      }

      return m(extent[0], new Date(+extent[1] + 1), k);
    };

    scale.tickFormat = function () {
      return format;
    };

    scale.copy = function () {
      return d3_time_scale(linear.copy(), methods, format);
    };

    return d3.rebind(scale, linear, "range", "rangeRound", "interpolate", "clamp");
  }

  function d3_time_scaleExtent(domain) {
    var start = domain[0],
        stop = domain[domain.length - 1];
    return start < stop ? [start, stop] : [stop, start];
  }

  function d3_time_scaleDate(t) {
    return new Date(t);
  }

  function d3_time_scaleFormat(formats) {
    return function (date) {
      var i = formats.length - 1,
          f = formats[i];

      while (!f[1](date)) {
        f = formats[--i];
      }

      return f[0](date);
    };
  }

  function d3_time_scaleSetYear(y) {
    var d = new Date(y, 0, 1);
    d.setFullYear(y);
    return d;
  }

  function d3_time_scaleGetYear(d) {
    var y = d.getFullYear(),
        d0 = d3_time_scaleSetYear(y),
        d1 = d3_time_scaleSetYear(y + 1);
    return y + (d - d0) / (d1 - d0);
  }

  var d3_time_scaleSteps = [1e3, 5e3, 15e3, 3e4, 6e4, 3e5, 9e5, 18e5, 36e5, 108e5, 216e5, 432e5, 864e5, 1728e5, 6048e5, 2592e6, 7776e6, 31536e6];
  var d3_time_scaleLocalMethods = [[d3.time.second, 1], [d3.time.second, 5], [d3.time.second, 15], [d3.time.second, 30], [d3.time.minute, 1], [d3.time.minute, 5], [d3.time.minute, 15], [d3.time.minute, 30], [d3.time.hour, 1], [d3.time.hour, 3], [d3.time.hour, 6], [d3.time.hour, 12], [d3.time.day, 1], [d3.time.day, 2], [d3.time.week, 1], [d3.time.month, 1], [d3.time.month, 3], [d3.time.year, 1]];
  var d3_time_scaleLocalFormats = [[d3.time.format("%Y"), d3_true], [d3.time.format("%B"), function (d) {
    return d.getMonth();
  }], [d3.time.format("%b %d"), function (d) {
    return d.getDate() != 1;
  }], [d3.time.format("%a %d"), function (d) {
    return d.getDay() && d.getDate() != 1;
  }], [d3.time.format("%I %p"), function (d) {
    return d.getHours();
  }], [d3.time.format("%I:%M"), function (d) {
    return d.getMinutes();
  }], [d3.time.format(":%S"), function (d) {
    return d.getSeconds();
  }], [d3.time.format(".%L"), function (d) {
    return d.getMilliseconds();
  }]];
  var d3_time_scaleLinear = d3.scale.linear(),
      d3_time_scaleLocalFormat = d3_time_scaleFormat(d3_time_scaleLocalFormats);

  d3_time_scaleLocalMethods.year = function (extent, m) {
    return d3_time_scaleLinear.domain(extent.map(d3_time_scaleGetYear)).ticks(m).map(d3_time_scaleSetYear);
  };

  d3.time.scale = function () {
    return d3_time_scale(d3.scale.linear(), d3_time_scaleLocalMethods, d3_time_scaleLocalFormat);
  };

  var d3_time_scaleUTCMethods = d3_time_scaleLocalMethods.map(function (m) {
    return [m[0].utc, m[1]];
  });
  var d3_time_scaleUTCFormats = [[d3.time.format.utc("%Y"), d3_true], [d3.time.format.utc("%B"), function (d) {
    return d.getUTCMonth();
  }], [d3.time.format.utc("%b %d"), function (d) {
    return d.getUTCDate() != 1;
  }], [d3.time.format.utc("%a %d"), function (d) {
    return d.getUTCDay() && d.getUTCDate() != 1;
  }], [d3.time.format.utc("%I %p"), function (d) {
    return d.getUTCHours();
  }], [d3.time.format.utc("%I:%M"), function (d) {
    return d.getUTCMinutes();
  }], [d3.time.format.utc(":%S"), function (d) {
    return d.getUTCSeconds();
  }], [d3.time.format.utc(".%L"), function (d) {
    return d.getUTCMilliseconds();
  }]];
  var d3_time_scaleUTCFormat = d3_time_scaleFormat(d3_time_scaleUTCFormats);

  function d3_time_scaleUTCSetYear(y) {
    var d = new Date(Date.UTC(y, 0, 1));
    d.setUTCFullYear(y);
    return d;
  }

  function d3_time_scaleUTCGetYear(d) {
    var y = d.getUTCFullYear(),
        d0 = d3_time_scaleUTCSetYear(y),
        d1 = d3_time_scaleUTCSetYear(y + 1);
    return y + (d - d0) / (d1 - d0);
  }

  d3_time_scaleUTCMethods.year = function (extent, m) {
    return d3_time_scaleLinear.domain(extent.map(d3_time_scaleUTCGetYear)).ticks(m).map(d3_time_scaleUTCSetYear);
  };

  d3.time.scale.utc = function () {
    return d3_time_scale(d3.scale.linear(), d3_time_scaleUTCMethods, d3_time_scaleUTCFormat);
  };

  d3.text = function () {
    return d3.xhr.apply(d3, arguments).response(d3_text);
  };

  function d3_text(request) {
    return request.responseText;
  }

  d3.json = function (url, callback) {
    return d3.xhr(url, "application/json", callback).response(d3_json);
  };

  function d3_json(request) {
    return JSON.parse(request.responseText);
  }

  d3.html = function (url, callback) {
    return d3.xhr(url, "text/html", callback).response(d3_html);
  };

  function d3_html(request) {
    var range = d3_document.createRange();
    range.selectNode(d3_document.body);
    return range.createContextualFragment(request.responseText);
  }

  d3.xml = function () {
    return d3.xhr.apply(d3, arguments).response(d3_xml);
  };

  function d3_xml(request) {
    return request.responseXML;
  }

  return d3;
}();

/* harmony default export */ var d3_v3 = (d3_v3_d3);
// CONCATENATED MODULE: ./src/spiderModel.js
/*
this doesnt return something d3 would like to use,
fix to look like:

    [
        {
            name: "process1",
            data: [
                {
                    name: "host1",
                    memory: 10
                }
            ]
        }
    ]

i still dont know how to use that with d3
    just draw each group at once?
        => draw group markers, host markers, host labels

    draw group labels later

arcsize = size of each group * totalGroups

*/


var modelUtil = {
  groupDataA: function groupDataA(data, groups) {
    var combined = [],
        currentGroup;

    underscore_default.a.each(groups, function (group, i) {
      // combined[group] = [];
      // currentGroup = combined[group];
      currentGroup = {
        name: group,
        data: []
      };
      combined.push(currentGroup);

      underscore_default.a.each(data, function (host, k) {
        if (host[group] !== undefined) {
          currentGroup.data.push({
            name: k,
            memory: host[group]
          }); // currentGroup[host.name] = host[group];
        }
      });
    });

    return combined;
  },
  countItems: function countItems(groupedData) {
    var numItems = 0;

    underscore_default.a.each(groupedData, function (group) {
      underscore_default.a.each(group.data, function () {
        numItems++;
      });
    });

    return numItems;
  },

  /*
  main differences:
      1. there is only one grouping key, which has no value we are interested in
          => group: "DataCenterA"
          => versus: "python" => memory usage
      2. The group key has no value associated that we are trying to utilize.
   whichever metric is used, it will hvae to be combined across many things
      => memory should be combined across all processes if we are just reporting one memory statistic
  */
  groupDataB: function groupDataB(data, groups, groupKey, metric) {
    var combined = [],
        currentGroup;

    underscore_default.a.each(groups, function (group, i) {
      currentGroup = {
        name: group,
        data: []
      };
      combined.push(currentGroup);

      underscore_default.a.each(data, function (host, k) {
        if (host[groupKey] === group) {
          currentGroup.data.push({
            name: k,
            memory: host[metric]
          }); // currentGroup[host.name] = host[metric];
        }
      });
    });

    return combined;
  },
  countByGroup: function countByGroup(data, groupKey) {
    var byGroup = {},
        arr = [];
    jquery_3_5_0_min_default.a.each(data, function (i, v) {
      if (byGroup[v[groupKey]] === undefined) {
        byGroup[v[groupKey]] = 0;
      }

      byGroup[v[groupKey]]++;
    }); // must use array - cant sort an object

    jquery_3_5_0_min_default.a.each(byGroup, function (k, v) {
      var obj = {};
      obj.count = v;
      obj[groupKey] = k;
      arr.push(obj);
    }); // this must be sorted the same way prepareData sorts
    // so the data is drawn in the same order

    return underscore_default.a.sortBy(arr, function (v) {
      return v[groupKey];
    });
  },
  prepareData: function prepareData(data, groupKey) {
    var prepared;
    /*
    we must sort the data by group because
    we have to draw the hosts together by group
    */

    prepared = underscore_default.a.sortBy(data, function (v) {
      return v[groupKey];
    });
    return prepared;
  }
};
/* harmony default export */ var spiderModel = (modelUtil);
// CONCATENATED MODULE: ./src/circleGrad.js
/*
Handles all gradient interactions, encapsulating DOM operations

Expects a d3 element, container
Container will store all the gradient definitions
*/




var circleGrad_Grad = function Grad(parentContainer, id, containerClass, radius) {
  var gradientContainer,
      gradient,
      containers,
      $containers,
      $parentContainer,
      self = this,
      toRadiusScale,
      numColors = 0,
      edgeDistance = 1.0;
  containerClass = '.' + containerClass;
  $parentContainer = jquery_3_5_0_min_default()(parentContainer.node());
  containers = parentContainer.selectAll(containerClass);
  $containers = $parentContainer.find(containerClass);
  toRadiusScale = d3_v3.scale.linear().domain([100, 0]).range([0, radius]);

  function getNumCircles() {
    return $containers.eq(0).find("circle").length;
  }

  function iterateCircles(cb) {
    $containers.each(function () {
      jquery_3_5_0_min_default()(this).children().each(function (i) {
        var $circle = jquery_3_5_0_min_default()(this);
        cb($circle, i);
      });
    });
  }

  function correctNewCircleColors(newCircles) {
    var $circle, $prev, prevColor, $next;

    underscore_default.a.each(newCircles[0], function (circle) {
      $circle = jquery_3_5_0_min_default()(circle);
      $prev = $circle.prev();
      $next = $circle.next();

      if ($prev !== undefined && $prev.length) {
        prevColor = $prev.attr('fill');
        $prev.attr('fill', $circle.attr('fill'));

        if ($next.length) {
          $circle.attr('fill', prevColor);
        }
      }
    });
  } // When inserting, we must maintain order according to the stop offset


  this.insert = function (colorData) {
    var newColorCircles, $container, container, prevRadius, newColorPos, found, $circle, circle, currentRadius, $this, foundIdx;

    if (numColors === 0) {
      /*
      These can be inserted all at once because 
      there's no order to enforce yet
      */
      appendNewColorCircle(containers, colorData.color, 0);
      newColorCircles = appendNewColorCircle(containers, colorData.color, colorData.position);
    } else {
      /*
      This assumes that the first container contains identical items
      so we can use it to figure out the proper insertion point
      */
      $container = $containers.eq(0);
      newColorPos = toRadiusScale(colorData.position);
      found = false;
      /*
      Find a spot to insert the new color
      We want to keep the DOM sorted, so everything
      overlaps properly.
      */

      $container.children().each(function (i) {
        $circle = jquery_3_5_0_min_default()(this);
        currentRadius = Number($circle.attr('r'));

        if (prevRadius === undefined) {
          if (currentRadius < newColorPos) {
            found = true;
            foundIdx = i;
            return false;
          } else {
            prevRadius = currentRadius;
          }
        } else {
          if (prevRadius > newColorPos && newColorPos >= currentRadius) {
            found = true;
            foundIdx = i;
            return false;
          } else {
            prevRadius = currentRadius;
          }
        }
      });

      if (found) {
        $containers.each(function () {
          $container = jquery_3_5_0_min_default()(this);
          container = d3_v3.select($container[0]);
          circle = container.append('circle').attr('r', toRadiusScale(colorData.position)).attr('fill', colorData.color) // This class is used so we can make a selection later
          // it's a bit of a hack
          .attr('class', 'temp__');
          $circle = jquery_3_5_0_min_default()(circle.node());
          $container.children().eq(foundIdx).before($circle);
        });
        newColorCircles = $containers.find('.temp__');
        newColorCircles = d3_v3.selectAll(newColorCircles);
        newColorCircles.classed('temp__', false);
        correctNewCircleColors(newColorCircles);
      } else {
        /*
        If we didn't find a spot, it means we must insert at the bottom end
        */
        newColorCircles = appendNewColorCircle(containers, colorData.color, colorData.position);
        correctNewCircleColors(newColorCircles);
      }
    }

    numColors++;
    self.logGrad();
    return newColorCircles;
  };
  /*
  Strategy for inserting hard edges:
      Two stops are inserted
          1. Right edge - uses the previous (in the svg) color
          2. Left Edge - contains the original color
      The edges are placed close to each other (1% apart) so that they create a hard edge
       The stops move together. Also, the right stop color may change when new colors are added.
       The edges are not saved, but are instead reconstructed when the user reloads the page.
      This just cuts down on the amount of data to send / bloat.
  */


  this.insertHardEdge = function (colorData) {
    var $circle;
    $circle = this.insert(colorData);
    return $circle;
  };

  this.remove = function (circles) {
    var $circle, $circles, $prev, color;
    $circle = jquery_3_5_0_min_default()(circles[0][0]);
    $circles = jquery_3_5_0_min_default()(circles);
    color = $circle.attr('fill');

    if (isBottomEnd($circle)) {
      $circles.each(function () {
        $prev = jquery_3_5_0_min_default()(this).prev();
        color = $prev.prev().attr('fill');
        $prev.attr('fill', color);
      });
    } else {
      /*
      We must fill in the void from removing this circle
      */
      $circles.each(function () {
        jquery_3_5_0_min_default()(this).prev().attr('fill', color);
      });
    }

    circles.remove();

    if (isEmpty()) {
      $containers.find('circle').attr('fill', 'white');
    }

    numColors--;
  };

  this.clear = function () {
    $containers.find('circle').remove();
  }; // this.getHighest = function(){
  //     return $containers.find('circle').first();
  // };


  function appendNewColorCircle(containers, color, offset) {
    var circles = containers.append('circle').attr('r', toRadiusScale(offset)).attr('fill', color);
    return circles;
  } // this should work for jQuery or D3 elements 


  function setCirclePos(circle, pos) {
    if (underscore_default.a.isString(pos)) {
      pos = Number(pos);
    }

    circle.attr('r', toRadiusScale(pos));
  }
  /*
  only works if $a is a higher radius than $b
  the bottom of the elements (what $b might represent)
  has extra elements
  */


  function swapColors($a, $b) {
    var $bNext, $bPrev, $aNext, $aPrev, tempColor;
    $bNext = $b.next();
    $bPrev = $b.prev();
    $aNext = $a.next();
    $aPrev = $a.prev();
    tempColor = $b.attr('fill');
    $b.attr('fill', $a.attr('fill'));
    $a.attr('fill', tempColor);
  }
  /*
  The top end has a two circles
  The very top is actually always the radius of the whole container
  */


  function isTopEnd($circle) {
    return $circle.prev().prev().length === 0;
  }

  function isBottomEnd($circle) {
    return $circle.next().length === 0;
  }

  function isEmpty() {
    return $containers.eq(0).children().length < 2;
  }

  function copyToAllCircles($copyableContainer) {
    var $sources = $copyableContainer.children(),
        $source;
    iterateCircles(function ($circle, i) {
      $source = $sources.eq(i);
      $circle.attr('fill', $source.attr('fill'));
      $circle.attr('r', $source.attr('r'));
    });
  }

  this.moveHardStop = function (stop, pos) {
    if (pos > 100) {
      console.error("Out of range: 100 is the maximum, got ", pos);
    }

    if (stop !== undefined) {
      stop.attr('r', toRadiusScale(pos));
    } else {
      console.error('Stop is undefined');
    }
  };

  this.moveStop = function (circle, pos) {
    if (pos > 100) {
      console.error("Out of range: 100 is the maximum, got ", pos);
    }

    if (circle !== undefined) {
      var $prev, $next, prevOffset, nextOffset, $circle, inOrder, _isTopEnd, currentColor, circleColor, formerNextColor, nextColor, prevColor, scaledPos;

      $circle = jquery_3_5_0_min_default()(circle.node());
      inOrder = false;
      scaledPos = toRadiusScale(pos); // pos = toRadiusScale(pos);

      if (!inOrder) {
        $prev = $circle.prev();
        $next = $circle.next();

        if (getNumCircles() < 2) {
          inOrder = true;
          setCirclePos(circle, pos);
          return false;
        }

        if ($prev.length) {
          prevOffset = this.getOffset($prev);
        } else {
          prevOffset = null;
        }

        if ($next.length) {
          nextOffset = this.getOffset($next);
        } else {
          nextOffset = null;
        }
        /*
        Elements are arranged with the highest radius circle
        at the top and the lowest at the bottom.
        We work element-by-element because the list was sorted
        to begin with.
        */
        // Moving Down


        if (nextOffset !== null && scaledPos < nextOffset) {
          currentColor = $circle.prev().attr('fill');
          circleColor = $circle.attr('fill');
          formerNextColor = $circle.next().attr('fill');
          $circle.insertAfter($next);
          nextColor = $circle.next().attr('fill');
          $circle.attr('fill', formerNextColor);
          $circle.prev().attr('fill', currentColor);
          $circle.prev().prev().attr('fill', circleColor);
        } else if (prevOffset !== null && scaledPos > prevOffset) {
          // Moving Up
          currentColor = $circle.prev().attr('fill');
          circleColor = $circle.attr('fill');
          $circle.insertBefore($prev);
          prevColor = $circle.prev().attr('fill');
          $circle.attr('fill', prevColor);
          $circle.prev().attr('fill', currentColor);
          $circle.next().attr('fill', circleColor);
        }

        if (nextOffset == null) {
          currentColor = $circle.prev().attr('fill');
          circleColor = $circle.attr('fill');
          $circle.prev().attr('fill', currentColor);
          $circle.next().attr('fill', circleColor);
        }

        setCirclePos(circle, pos);
        copyToAllCircles($circle.parent());
      }
    }
  };

  this.updateColor = function (circles, color) {
    var $circle, $prev, $next;
    circles.each(function (d) {
      $circle = jquery_3_5_0_min_default()(this);
      $prev = $circle.prev();
      $next = $circle.next();

      if ($prev.length) {
        $prev.attr('fill', color);
      } // The last circle actually has
      // two circles sharing the same color:
      //     1. itself
      //     2. the next circle
      // ordinary circles only have the color of the previous swatch


      if ($next.length === 0) {
        $circle.attr('fill', color);
      }
    });
  };

  this.getOffset = function (stop) {
    if (stop === undefined) {
      return 0;
    }

    return Number(stop.attr('r'));
  };

  this.logGrad = function () {
    $containers.eq(0).children().each(function (i) {
      var $circle = jquery_3_5_0_min_default()(this);
      var colorCss = "color:" + $circle.attr('fill');
    });
  };
};

/* harmony default export */ var circleGrad = (circleGrad_Grad);
// EXTERNAL MODULE: ./src/Utils/ConfUtils.js
var ConfUtils = __webpack_require__(6);

// CONCATENATED MODULE: ./src/colorModel.js
function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }




var viewName = "home";
/*eslint func-names:"as-needed" */

var colorModel_ColorModel = function ColorModel(data, moduleId, storage) {
  var current,
      self = this; //colorRouter,ColorRouter;

  /*ColorRouter = Backbone.Router.extend({
      routes: {
          '/:param':"q",
      },
       q: function(query, params) {
          // splunk has functions for decoding the query string
          // and encoding
          // Splunk.util.queryStringToProp(Splunk.util.getHash())
      } 
  });
   colorRouter = new ColorRouter();
  // We can only start the history once, or it will throw an exception
  if(Backbone.history.started === undefined){
      Backbone.history.start({pushState: true});
      Backbone.history.started = true;    
  }*/

  this.current = {};
  this._current = {};
  this.data = [];

  function buildIndex() {
    underscore_default.a.each(self.data, function (swatch, i) {
      swatch._i = i;
    });
  }

  function _load(cb) {
    self.data = [];
    Object(ConfUtils["c" /* getConfData */])(viewName).then(function (response) {
      if (response.status === 200 && response.data && response.data.entry[0]) {
        var wholeObj = response.data.entry[0]["content"];
        var newData;

        if (wholeObj && wholeObj["".concat(moduleId, "_colorSelection")]) {
          newData = JSON.parse(wholeObj["".concat(moduleId, "_colorSelection")]);
        }

        if (newData === undefined) {
          return false;
        }

        underscore_default.a.each(newData, function (data, i) {
          cb(data);
        });
      }
    })["catch"](function (error) {
      console.debug("error while fetching user preference data:", error);
    });
    ; //storage.load(function(newData){

    /*
    This addresses a bug in Firefox (at least Firefox 23)
    If we touch the URL history during SVG DOM operations (as are expected to occur during load callbacks)
    then none of the clipping paths work. Weird! See JIRA NIX-370
    */
    // window.setTimeout(function(){
    //     relativeNav(newQuery);
    // }, 200);
    //});
    // self.reset();
  }

  ;
  /*
  add
  Adds data to the model.
  */

  this.add = function (swatchData) {
    this.data.push(swatchData);
    this._current = swatchData;
    /*
        in order to keep track of the last-added element, we store a reference
        within this._current
        This value is swapped in whenever we need to reference the latest element.
        We cannot simply reference the last array value of this.data[] because
        that list is sorted. We would likely get the wrong element if we just 
        picked the last.
    */
    // why sort 1 item?

    if (this.data.length > 1) {
      this.data = underscore_default.a.sortBy(this.data, 'y');
    }

    buildIndex();
  };

  this.remove = function (swatchData) {
    this.data.splice(swatchData._i, 1);
    buildIndex();
    this.save();
  };

  this.setCurrent = function (currentData) {
    self.current = currentData;
  };

  this.setToLatest = function () {
    self.setCurrent(this._current);
  };

  this.updateCurrent = function (newData) {
    jquery_3_5_0_min_default.a.extend(this.current, newData);
  };
  /*
      save
      data is optional, otherwise just uses internal data
  */


  function save(data) {
    var saveable = [];

    if (data === undefined) {
      data = self.data;
    }
    /*
    Some of the stuff in data[] is not governed by the model, so we remove that before saving.
    See the notes on this.load() for more information
    */


    underscore_default.a.each(data, function (v, k) {
      saveable.push(underscore_default.a.pick(v, ['color', 'y']));
    });

    Object(ConfUtils["e" /* saveConfData */])(viewName, _defineProperty({}, "".concat(moduleId, "_colorSelection"), JSON.stringify(saveable)));
  }

  this.save = underscore_default.a.debounce(save, 1000);
  /*
  load
  the decorator function allows the consumer to add whatever extra data they
  want to the items.
   While saving, the model will ignore /any/ property that isnt 'color' or 'y'
  This frees up a consumer to add any other properties they want, via the decorator.
  However, anything added there is not subject to any logic in the model.
  Anything that isn't 'y' or 'color' is not considered this model's responsibility.
   The decorator can also just act as an ordinary callback.
  */

  this.load = function (decorator) {
    var self = this;

    _load.call(this, function (item) {
      if (decorator === undefined) {
        self.add(item);
      } else {
        self.add(decorator(item.color, item.y));
      }
    });
  };

  this.reset = function () {
    // localStorage.spiderGraph = "[]";
    this.data = [];
    this._current = {};
    this.save();
  };
};

/* harmony default export */ var src_colorModel = (colorModel_ColorModel);
// CONCATENATED MODULE: ./src/colorPalette.js
/*eslint func-names: ["always"] */
var ColorPalette = function ColorPalette($el, onSelect, onClose) {
  var colors,
      $color,
      color,
      $swatches,
      $confirm,
      $topButtons,
      $bottomButtons,
      self = this,
      i,
      $exitButton;
  this.$el = $el;
  $swatches = $("<div class='swatches'></div>");
  $bottomButtons = $("<div class='bottomButtons'></div>");
  $topButtons = $("<div class='topButtons'></div>");
  $confirm = $('<button class="btn unixButton confirm">Confirm</button>');
  $exitButton = $('<button class="btn unixButton exit">X</button>');
  this.$el.append($swatches);
  this.$el.append($bottomButtons);
  this.$el.prepend($topButtons);
  $topButtons.append($exitButton);
  $bottomButtons.append($confirm);
  colors = ['#E8E8E8', '#C9C9C9', '#AFAFAF', '#000000', '#B6D6A7', '#7DBCA4', '#468AB8', '#F3D17D', '#F3B070', '#E47A56', '#C55559', '#912D47'];

  function populatePallet() {
    for (i = 0; i < colors.length; i++) {
      $color = $("<div class='swatch'></div>"); // we save this twice because it will guarantee the format
      // does not switch to rgb or hsl

      $color.attr('bg', colors[i]);
      $color.css('background-color', colors[i]);
      $swatches.append($color);
    }
  }

  populatePallet();
  $el.find('.swatch').on('click', function (e) {
    color = $(this).attr('bg');
    onSelect.call(this, color);
  });
  $exitButton.click(function () {
    self.close();
    onClose();
  });
  $confirm.click(function () {
    self.close();
    onClose();
  });

  this.open = function () {
    $el.show();
  };

  this.close = function () {
    $el.hide();
  };

  this.destroy = function () {
    $el.empty();
  };
};

/* harmony default export */ var src_colorPalette = (ColorPalette);
// CONCATENATED MODULE: ./src/util.js
/*
The angles for arcs are a little odd:
    => they start at 90 degrees
    => they run clockwise

0  
|  10
| /
|/______ 90

This contrasts with an ordinary unit circle:

90  
|  80
| /
|/______ 0

So we must subtract PI/2 radians
*/

/*
If these needed _ or $, they would need to be exported
in which case, they would probably go under an umbrella object (util.correctHalfHangle(), etc)
*/
var util_HALFPI = Math.PI / 2.0;
function correctArcAngle(theta) {
  return theta - util_HALFPI;
}
function buildTranslate(x, y) {
  return "translate(" + x + "," + y + ")";
}
function buildRotate(theta, centerX, centerY) {
  return "rotate(" + theta + "," + centerX + "," + centerY + ")";
}
function d3clone(selector) {
  var node;

  if (typeof selector === 'string') {
    node = d3.select(selector).node();
  } else {
    node = selector.node();
  }

  return d3.select(node.parentNode.insertBefore(node.cloneNode(true), node.nextSibling));
}
function percentToNum(percent) {
  return Number(percent.substr(0, percent.length - 1));
}
function roundTo(num, place) {
  var rounded;
  rounded = num * Math.pow(10, place);
  rounded = Math.round(rounded);
  return rounded / Math.pow(10, place);
}
function truncateText(text, length) {
  if (text.length < length) {
    return text;
  } else {
    return text.substr(0, length) + "..";
  }
}
function removeFromArray(arr, i) {
  var rest = arr.slice(i + 1);
  arr.length = i;
  Array.prototype.push.apply(arr, rest);
  return arr;
}
function makeSvgLink() {}
function escapeCss() {}
function getLabelFitting(text, radius, arcSize) {
  var x, minX, textWidth, fontWidth, fontSize, padding; // This would be more accurate if we copied the text to a temporary DOM node
  // and then measured from there. However, that would be much slower.

  fontSize = 10; // this should grab from the DOM

  fontWidth = fontSize / 1.45; // rough approximation, works for our font

  minX = radius / 2;
  padding = 5;
  textWidth = text.length * fontWidth;

  if (radius - textWidth > minX) {
    x = radius - textWidth - padding;
  } else {
    x = minX;
  }

  return {
    x: x,
    textWidth: textWidth,
    fontWidth: fontWidth
  };
}
function toBoolean(str) {
  if (str.toLowerCase() === 'true') {
    return true;
  } else {
    return false;
  }
}
function parseQueryString() {
  var queryBreak = window.location.href.indexOf('?');

  if (queryBreak > -1) {
    var query = window.location.href.slice(queryBreak);
    return Splunk.util.queryStringToProp(query);
  } else {
    return false;
  }
}
// CONCATENATED MODULE: ./src/color.js
/* eslint-disable func-names */

/*
Allows the user to specify a gradient
*/







var color_Color = function Color(svg, grad, range, rangeCircle, defaultColors, moduleId, radius, storage) {
  var box,
      picker,
      $picker,
      pickerEl,
      gutterHeight,
      gutterWidth,
      gutterPadding,
      gutterMax,
      gutterMin,
      gutterY,
      percentY,
      pickerWidth,
      pickerHeight,
      axisGroup,
      pickerIsActive = false,
      swatchSize = 10,
      numColors = 0,
      drag,
      scaleData,
      thresholdArc,
      scaleCircle,
      scaleToGrad,
      gripperOffset,
      data = [],
      self = this,
      colorModel,
      scaleToGutter,
      moduleIdSel = "#" + moduleId,
      $wrapper = jquery_3_5_0_min_default()(moduleIdSel),
      normalizeGutterScale,
      colorPalette,
      colorRouter,
      $paletteEl;
  colorModel = new src_colorModel(data, moduleId, storage);
  scaleData = d3_v3.scale.linear() // Winds up being reversed with how the dom is set up
  .domain([100, 0]).range(range);
  scaleCircle = d3_v3.scale.linear().domain(range).range(rangeCircle);
  gutterWidth = 20;
  gutterHeight = radius + 20;
  gutterY = gutterHeight - 10;
  gutterPadding = 5;
  gutterMax = gutterHeight - gutterPadding;
  gutterMin = 15; // magic number because of how the filter graphic is constructed
  // Scales
  ////////////////////////////

  scaleToGutter = d3_v3.scale.linear().domain([0, 100]).range([gutterMin, gutterMax]);
  normalizeGutterScale = scaleToGutter.invert;
  scaleToGrad = d3_v3.scale.linear().domain([gutterMin, gutterMax]).range([0, 100]);

  function scaleToCircle(x) {
    return scaleCircle(scaleData(x));
  } // Color Picker Setup
  ////////////////////////////
  // these are set in css
  // but these values are a little smaller


  pickerWidth = 150;
  pickerHeight = 200;
  $paletteEl = jquery_3_5_0_min_default()('#' + moduleId + '-palette'); // We use these two to encapsulate the state behavior as much as possible

  function closeColorPicker() {
    pickerIsActive = false;
  }

  colorPalette = new src_colorPalette($paletteEl, function (hex) {
    updateCurrentColor({
      color: hex
    });
    self.save();
  }, closeColorPicker);

  function loadDefault(colorA, colorB) {
    grad.clear();
    insertNewThreshold(colorA, 0);
    insertNewThreshold(colorB, 100);
  } // this isn't svg, so we use jquery instead of d3
  // otherwise, weird crap happens


  $picker = jquery_3_5_0_min_default()('#' + moduleId + '-picker'); // This fixes annoying image dragging behavior in firefox

  d3_v3.select('#' + moduleId + '-picker').selectAll('rect').attr('draggable', false);
  $wrapper.find(".pickerWrapper").bind("dragstart", function () {
    return false;
  }); // Cant setup the dom in the html because the color picker lib changes a bunch of junk

  $picker.append("<div class='confirmWrapper'><button class='btn btn-inverse confirm'>Confirm</button></div>");
  $picker.find('.confirm').click(function () {
    closeColorPicker();
    numColors++;
  }); // We only display the color picker when the user clicks appropriately

  $picker.hide(); // Threshold grid
  ////////////////////////////

  thresholdArc = d3_v3.svg.arc().startAngle(0).endAngle(Math.PI); // todo: better names, more consistent

  function insertGridArc(x) {
    var arc, thresholdCircle;
    arc = thresholdArc.outerRadius(function (x) {
      return scaleToCircle(x);
    }).innerRadius(function (x) {
      return scaleToCircle(x);
    });
    thresholdCircle = svg.selectAll('thresholdCircle').data([x]).enter().append('path').attr('class', 'thresholdCircle').attr('d', arc).each(function (d) {
      this._highest = d;
    });
    return thresholdCircle;
  }

  function thresholdTween(d) {
    var interp;
    interp = d3_v3.interpolate(this._highest, d);
    this._highest = d;
    return function (t) {
      thresholdArc.outerRadius(function () {
        return scaleToCircle(interp(t));
      });
      thresholdArc.innerRadius(function () {
        return scaleToCircle(interp(t));
      });
      return thresholdArc();
    };
  }

  axisGroup = d3_v3.select(moduleIdSel + ' .axisGroup .axis').append('g').attr('id', moduleId + '-pickedColors').attr('transform', buildTranslate(55, -gutterHeight));
  box = svg.select('.axisGroup').insert('rect', ':first-child').attr('x', -30).attr('y', -gutterY).attr('width', gutterWidth).attr('height', gutterHeight).attr('class', 'colorUI').attr("rx", "5").attr('filter', "url(" + moduleIdSel + "-inset-shadow)")
  /*
  Handle inserting new gradient swatches
  */
  .on('click', function () {
    var bounding, y;
    bounding = d3_v3.event.target.getBoundingClientRect();
    y = (d3_v3.event.clientY - bounding.top) / gutterHeight * 100;

    if (!pickerIsActive) {
      insertNewThreshold("#000000", y);
      self.save();
      colorModel.setToLatest(); // latest being the one we just added via insertNewThreshold

      openColorPicker(d3_v3.event.offsetX, d3_v3.event.offsetY);
    } // todo: need an else here to handle requests for new colors when picker already open. Ask Cary

  });

  function updateCurrentColor(updates) {
    colorModel.updateCurrent(updates);
    updateGridArc(colorModel.current);
    updateSwatch(colorModel.current);
  } // gridData.y should be in the range [0..100]
  // it's scaled later


  function updateGridArc(gridData) {
    gridData.gridArc.data([gridData.y]).transition().duration().attrTween("d", thresholdTween);
  }

  function updateSwatch(swatchData) {
    swatchData.swatch.select('rect').attr('fill', swatchData.color);
    swatchData.swatch.attr('y', swatchData.y / 100 * gutterHeight + swatchSize / 2);
    grad.moveHardStop(swatchData.gradStop, swatchData.y); // grad.updateColor(swatchData.gradStop, swatchData.color);

    grad.updateColor(swatchData.gradStop, swatchData.color);
  }
  /*
  note that the reference to the current gradient is bound in a closure
  this isnt the most flexible way of doing this
   we are also storing references in data[] but they are not used at the moment.
  color, y, gradStop, arc
  */


  function insertSwatch(swatchData) {
    var swatch,
        yGrad,
        y = swatchData.y,
        color = swatchData.color,
        gradStop = swatchData.gradStop,
        gradStopEdge = swatchData.gradStopEdge,
        firstClickTime = null,
        doubleClickTimer,
        drag,
        yGutter,
        gripperStart,
        gripperEnd,
        gripperStartY;
    drag = d3_v3.behavior.drag() // .origin(Object) // this doesnt work but supposedly handles origin dragging
    .on("drag", handleDrag);

    function handleDrag(d) {
      var bounding, y, x, el, yOffset;
      bounding = svg.select('.colorUI').node().getBoundingClientRect();
      x = d3_v3.event.sourceEvent.clientX - bounding.left - swatchSize; // todo: implement - minor shift when dragging
      // offsetY = d3.event;

      yOffset = 0; //todo: this should be outputting scaled data based upon the height of the UI

      yGutter = Math.max(gutterMin, Math.min(gutterMax, d3_v3.event.y)); // This gives a nice "snapping" behavior when dragging off the swatch
      // The user can drag off the swatch when they want to delete a threshold

      if (Math.abs(x) > 35) {
        d3_v3.select(this).attr('transform', buildTranslate(x, yGutter - yOffset));
        deleteThreshold(swatchData);
        closeColorPicker();
      } else {
        d3_v3.select(this).attr('transform', buildTranslate(0, yGutter - yOffset));
      }

      yGrad = scaleToGrad(yGutter);
      grad.moveStop(gradStop, yGrad); // grad.moveHardStop(gradStop, yGrad);
      // grad.moveEdgeStop(gradStopEdge, yGrad);

      swatchData.y = normalizeGutterScale(yGutter);
      updateGridArc({
        gridArc: swatchData.gridArc,
        y: swatchData.y
      });
      self.save();
    } // inserting a new swatch


    swatch = axisGroup.append('g').attr('class', 'swatchGroup').attr('transform', buildTranslate(0, scaleToGutter(swatchData.y))).call(drag).on('click', function () {
      if (firstClickTime === null) {
        firstClickTime = d3_v3.event.timeStamp;
      } else {
        if (d3_v3.event.timeStamp - firstClickTime < 600) {
          // todo: this threshold should be tweaked
          openColorPicker(d3_v3.event.offsetX, d3_v3.event.offsetY);
          colorModel.setCurrent(swatchData);
          firstClickTime = d3_v3.event.timeStamp;
        } else {
          firstClickTime = d3_v3.event.timeStamp;
        }
      }
    });
    swatch.append('rect').attr('class', 'swatchColor').attr('width', swatchSize).attr('height', swatchSize).attr('rx', 2).attr('ry', 2).attr('fill', color);
    gripperStart = 1;
    gripperEnd = swatchSize - 2;
    gripperStartY = 2;
    swatch.append('line').attr('x1', gripperStart).attr('x2', gripperEnd).attr('y1', gripperStartY).attr('y2', gripperStartY).attr('class', 'gripperMark') // this gets nice 1px lines
    // todo: fix these offsets for chrome/firefox; off by one pixel for chrome
    .attr('shape-rendering', "crispEdges");
    swatch.append('line').attr('x1', gripperStart).attr('x2', gripperEnd).attr('y1', gripperStartY + 2).attr('y2', gripperStartY + 2).attr('class', 'gripperMark').attr('shape-rendering', "crispEdges");
    swatch.append('line').attr('x1', gripperStart).attr('x2', gripperEnd).attr('y1', gripperStartY + 4).attr('y2', gripperStartY + 4).attr('class', 'gripperMark').attr('shape-rendering', "crispEdges");
    return swatch;
  }

  function buildNewThreshold(color, y) {
    var arc, gradStop, swatchData, swatch, gradStopData; // TODO: do we still need this? If so, make it a method on grad

    if (numColors === 0) {// d3.select(grad.getHighest()).remove();
    }

    numColors++;
    arc = insertGridArc(y);
    gradStopData = {
      'color': color,
      'position': y
    }; // gradStop = grad.insert(gradStopData);

    gradStop = grad.insertHardEdge(gradStopData);
    swatchData = {
      'color': color,
      'y': y,
      'gridArc': arc,
      'gradStop': gradStop
    };
    swatch = insertSwatch(swatchData);
    swatchData.swatch = swatch;
    return swatchData;
  }

  function insertNewThreshold(color, y) {
    var threshold = buildNewThreshold(color, y);
    colorModel.add(threshold);
  }

  function deleteThreshold(thresholdData) {
    grad.remove(thresholdData.gradStop);
    thresholdData.gridArc.remove();
    thresholdData.swatch.remove();
    colorModel.remove(thresholdData);
  }

  function openColorPicker(clickX, clickY) {
    pickerIsActive = true;
    var x, y, bounding, wrapperLeft, wrapperTop;
    bounding = d3_v3.select("#" + moduleId + " g.wrapper").node().getBoundingClientRect();
    wrapperLeft = $wrapper.offset().left;
    wrapperTop = $wrapper.offset().top;
    x = bounding.left - pickerWidth - gutterWidth * 4 - wrapperLeft;
    y = bounding.top - wrapperTop;
    x = clickX - pickerWidth - gutterWidth * 5;

    if (wrapperLeft < pickerWidth) {
      x = 0;
    }

    y = clickY;
    colorPalette.open();
    colorPalette.$el.css({
      left: x,
      top: clickY
    });
  }

  this.load = function (newData) {
    // colorModel.load(function(data){
    //     insertNewThreshold(data.color, data.y);
    // });
    colorModel.load(buildNewThreshold);
  };

  this.save = function () {
    colorModel.save();
  };

  this.clearDisplay = function () {
    grad.clear();
    d3_v3.selectAll("".concat(moduleIdSel, "-pickedColors g.swatchGroup")).remove();
    svg.selectAll(".thresholdCircle").remove();
    colorModel.reset();
  };

  this.destroy = function () {
    colorPalette.destroy();
  };
  /*
  todo: reoragnize this
  i dont like how this is all the way down here, when it is so important
  */


  this.load();
};

/* harmony default export */ var src_color = (color_Color);
// EXTERNAL MODULE: ./src/globalSelections.js
var globalSelections = __webpack_require__(22);

// CONCATENATED MODULE: ./src/spider.js









var hostViewName = 'hosts';
var hostRedirectLink = 'hosts';
/* harmony default export */ var spider = (function (el, moduleId, width, height, labelsOn, storage) {
  var svg,
      numArcSegments,
      PI2 = Math.PI * 2.0,
      PI = Math.PI,
      HALFPI = Math.PI / 2.0,
      RAD2DEG = 180 / Math.PI,
      DEG2RAD = Math.PI / 180,
      arcSize,
      colors,
      arc,
      radius,
      scale,
      reverseScale,
      max,
      isReady = false,
      gridMarkerRadii = [],
      groupArc,
      grad,
      hostSlices = [],
      peaks = [],
      peakDuration = 10000,
      colorPicker,
      moduleIdSel = "#" + moduleId,
      $wrapper = el,
      arcTweenArc,

  /*
  We have to store unique IDs for groups so we can go back and select them later
  There's probably a better way of doing this but this is fine for how
  my elements are organized now.
  */
  groupElementIds = {},
      groupKey = "group",
      circleGradContainer = 'circleGradContainer',
      groupAngles = [];

  if (width < height) {
    radius = width / 1.8;
  } else {
    radius = height / 2.4;
  }

  var left = width / 4;
  var top = height / 1.85;
  d3_v3.select($wrapper).select("svg").attr({
    'width': width,
    'height': height
  }).append("g").attr("transform", "translate(" + left + "," + top + ")").attr('class', 'wrapper');
  /*
  plot should be called first
  we could do this in the constructor, but then there is no way to instantiate the graph and draw it later.
  Could do it in constructor and provide the user with a parameter for initial rendering.
  */

  this.plot = function (data, min, max) {
    var currentAngle = 0,
        numHosts = 0,
        bgData = [radius],
        prevGroupSize = 0;
    resetScale(data, min, max);
    isReady = true;
    numArcSegments = spiderModel.countItems(data); // in radians

    arcSize = PI / numArcSegments;
    arcTweenArc = d3_v3.svg.arc().innerRadius(0).startAngle(0).endAngle(arcSize);
    svg = d3_v3.select(moduleIdSel + ' svg g.wrapper'); // Background
    /////////////////////

    svg.selectAll('bg').data(bgData).enter().append('path').attr('d', function (d) {
      arc = d3_v3.svg.arc().innerRadius(0).startAngle(0).outerRadius(d).endAngle(PI);
      return arc();
    }).attr('class', 'bg'); // Temp. grad circles
    /////////////////////
    // let tempCircleData = [radius, radius-100, radius-200];

    var tempCircleData = [radius, radius - 100, radius - 200];
    var tempCircleGroup = svg.append('defs').attr('class', 'gradCircle').attr('clip-path', 'url(#tempClipPath)');
    tempCircleGroup.selectAll('bgCircle').data(tempCircleData).enter().append('circle').attr('r', function (d) {
      return d;
    }).attr('fill', function (d, i) {
      if (d === radius) {
        return '#D9B1DE';
      } else if (d === radius - 100) {
        return '#B1BADE';
      } else {
        return '#B1DEDE';
      }
    }).attr('id', function (d, i) {
      return "bgCircle-" + i;
    }).attr('class', 'tempCircle');
    var tempClipGroup = svg.append('clippath').attr('id', 'tempClipPath'); // Draw Hosts, Groups, Peaks
    ///////////////////////////////

    underscore_default.a.each(data, function (group, j) {
      var group_name = group.name.replace(/[ #\.]/g, '_'),
          currentGroup = svg.append('g').attr('transform', function () {
        var currentGroupAngle = arcSize * prevGroupSize;
        groupAngles.push(currentGroupAngle);
        return buildRotate(currentGroupAngle * RAD2DEG, 0, 0);
      }) // .attr('id', moduleId + '-' +group.name)
      .attr('id', function (d, i) {
        var id = underscore_default.a.uniqueId('group-');

        groupElementIds[group.name] = id;
        return id;
      }).attr('class', 'group');
      var hostGroup = currentGroup.selectAll('hostGroup').data(group.data).enter() // .append('g')
      .append('g').attr('transform', function (d, i) {
        return buildRotate(arcSize * i * RAD2DEG, 0, 0);
      }).attr('class', 'hostGroup').on('click', function (d) {
        var params = {
          selected_category: data[0].name,
          selected_group: JSON.stringify(globalSelections["a" /* controlSelections */]["".concat(moduleId, "_selectedGroups")]),
          selected_host: undefined
        };
        Object(ConfUtils["e" /* saveConfData */])(hostViewName, params).then(function () {
          window.open(hostRedirectLink, "_self");
        });
      }); // this lines separates groups

      currentGroup.append('line').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', -(radius + 50)).attr('class', 'groupMarker');
      peaks[j] = hostGroup.append('path').attr('class', 'peak').each(function (d) {
        var peak = this;
        this._highest = d.metric;
        this._resetTimer = window.setInterval(function () {
          (function (peak) {
            resetPeak(peak);
          })(peak);
        }, peakDuration);
      });
      /* 
          this will eventually turn into an arc
          via update() => arctween()
           we animate the clipping paths so the gradient
          does not scale. See setupHostBackground() for more info.
      */

      hostSlices[j] = hostGroup.append('g').append('clipPath').attr('id', function (d, i) {
        var id = moduleId + "-hostClip-" + group_name + "-" + i;
        return id;
      }).append('path') // this may be used in the future
      // .attr('fill', function(d,i){
      //     return "hsl("+150+","+(i*10+20)+"%,"+((i*10+30)-15) +"%)";
      // })
      .each(function (d) {
        this._current = d.metric;
      }).attr('id', function (d, i) {
        var id = moduleId + "-hostClipPath-" + group_name + "-" + i;
        return id;
      }); // tempClipGroup.selectAll('path')
      //     .data(group.data).enter()
      //         .append('use')
      //             .attr('xlinkhref', function(d,i){
      //                 let id = '#'+moduleId+"-hostClipPath-"+group.name+"-"+i;
      //                 return id;
      //             })
      //             // .each(function(d) { this._current = d.metric; });
      // $("use[xlinkhref]").each(function(){
      //     let val = $(this).attr('xlinkhref');
      //     $(this).attr('xlink:href', val);
      //     $(this).removeAttr('xlinkhref');
      // })

      var circleGradContainer = currentGroup.selectAll('circleGradContainer');
      setupHostBackground(hostGroup, group_name, j);
      prevGroupSize += group.data.length;
    }); // Draw Gradients
    //////////////////////


    grad = new circleGrad(svg, moduleId + '-hostBg', circleGradContainer, radius);
    jquery_3_5_0_min_default()(".logGrad").on('click', function () {
      grad.logGrad();
    }); // Gradients must be assigned

    svg.selectAll('path.slice').style("fill", function (d, i) {
      return "url(#" + moduleId + "-hostBg)";
    });
    this.update(data);
    drawGridMarkers(4);
    drawHostMarkers(data);
    drawGroupMarkers(data, groupAngles); // This goes last because it depends upon a complete dom

    colorPicker = new src_color(svg, grad, [0, max], [0, radius], ["#ff5405", "#ffb76b"], moduleId, radius, storage);
    jquery_3_5_0_min_default()($wrapper).find(".loadTest").on("click", function () {
      colorPicker.load();
    });
    jquery_3_5_0_min_default()($wrapper).find(".clearTest").on("click", function () {
      colorPicker.clearDisplay();
    });
  };

  this.update = function (newData) {
    if (!isReady) {
      throw "Must run plot() first";
    }

    removeGroupMarkers();
    drawGroupMarkers(newData, groupAngles);

    underscore_default.a.each(newData, function (group, i) {
      hostSlices[i].data(group.data);
      hostSlices[i].transition().duration(500) // .duration(onlyAnimateChanged)
      .attrTween("d", arcTween);
      peaks[i].data(group.data);
      peaks[i].transition().duration(400).attrTween("d", peakTween); // peaks[i].transition().duration(onlyAnimateHigherPeaks).attrTween("d", peakTween);
    });
  };

  this.destroy = function () {
    if (svg !== undefined) {
      jquery_3_5_0_min_default()(svg.node()).empty();
    }

    if (colorPicker !== undefined) {
      colorPicker.destroy();
    }
  };

  function resetScale(data, min, max) {
    scale = d3_v3.scale.linear().domain([0, max]).range([0, radius]); // This allows us to draw the y-axis values
    // we have to translate from the circle's units to the domain values

    reverseScale = scale.invert;
  } // Other arc animation
  ////////////////////////////


  function onlyAnimateChanged(d, i) {
    if (d.metric === d._current) {
      return false;
    } else {
      return 500;
    }
  } // Peak Animation
  ////////////////////////////


  function onlyAnimateHigherPeaks(d, i) {
    if (d.metric > this.highest) {
      return 400;
    } else {
      return 0;
    }
  }

  function arcTween(d, i) {
    var interp;
    interp = d3_v3.interpolate(this._current, d.metric);
    this._current = d.metric;
    return function (t) {
      arcTweenArc.outerRadius(function () {
        return scale(interp(t));
      });
      return arcTweenArc();
    };
  }

  function peakTween(d, i) {
    var arc, interp, peak;
    peak = this;
    arc = d3_v3.svg.arc().startAngle(0).endAngle(arcSize);

    if (d.metric > this._highest) {
      // new peak
      interp = d3_v3.interpolate(this._highest, d.metric);
      this._highest = d.metric;

      if (this._resetTimer !== undefined || this._resetTimer !== null) {
        // must remove the old timer in order to restart the interval
        window.clearTimeout(this._resetTimer);
        this._resetTimer = window.setInterval(function () {
          (function (peak) {
            resetPeak(peak);
          })(peak);
        }, peakDuration);
      }
    } else {
      interp = d3_v3.interpolate(this._highest, this._highest);
    }

    return function (t) {
      arc.outerRadius(function () {
        return scale(interp(t));
      });
      arc.innerRadius(function () {
        return scale(interp(t));
      });
      return arc();
    };
  }

  function resetPeak(peak) {
    d3_v3.select(peak).transition().duration(700).attrTween("d", tweenToZero);
  }

  function tweenToZero(d) {
    var arc, interp;
    arc = d3_v3.svg.arc().startAngle(0).endAngle(arcSize);
    interp = d3_v3.interpolate(this._highest, d.metric);
    this._highest = d.metric;
    return function (t) {
      arc.outerRadius(function () {
        return scale(interp(t));
      });
      arc.innerRadius(function () {
        return scale(interp(t));
      });
      return arc();
    };
  }
  /*
  This is clipped by the hosts slices themselves
  We must do this becuase we do not want the gradients to scale
  with the slices. This lets us have real threshhold values
  on the gradient. 
  */


  function setupHostBackground(hostGroup, groupName, j) {
    var hostBg, arc, gradContainer;
    arc = d3_v3.svg.arc().innerRadius(0).startAngle(0).endAngle(arcSize).outerRadius(radius);
    hostBg = hostGroup.append('path').attr('d', arc).attr('class', 'hostBg');
    /*
    These defer statements ensure that Firefox will render 
    the clipping appropriately. This bug is reproducable in Firefox 23 at least.
    See JIRA: NIX-370
    */

    underscore_default.a.defer(function () {
      hostBg.attr('clip-path', function (d, i) {
        return "url(#" + moduleId + "-hostClip-" + groupName + "-" + i + ")";
      });
    });

    gradContainer = hostGroup.append('g').attr('class', 'circleGradContainer');

    underscore_default.a.defer(function () {
      gradContainer.attr('clip-path', function (d, i) {
        return "url(#" + moduleId + "-hostClip-" + groupName + "-" + i + ")";
      });
    });
  }
  /*
  These are the concentric circles that show the y-axis
  This also draws the y-axis itself
   If the user changes the scale, we need to animate the scales to new positions
  We may also need to draw new scale markers entirely
  Right now this doesnt do any of that!
  */


  function drawGridMarkers(num) {
    var i,
        gridArc,
        markerEnter,
        axisSubgroup,
        line,
        axis,
        grid,
        gapDistance = 80;

    for (i = 0; i < num; i++) {
      // we use i+1 here because otherwise we dont get a complete range
      gridMarkerRadii[i] = radius / num * (i + 1);
    }

    gridArc = d3_v3.svg.arc().innerRadius(0).outerRadius(function (d, i) {
      return d;
    }).startAngle(0).endAngle(PI);
    markerEnter = svg.append('g').attr('class', 'axisGroup');
    axis = markerEnter.append('g').attr('class', 'axis').attr('transform', buildTranslate(-gapDistance, 0)).selectAll('gridMarker').data(gridMarkerRadii).enter();
    grid = markerEnter.selectAll('gridMarker').data(gridMarkerRadii).enter();
    grid.append('path').attr('d', gridArc).attr('class', 'gridMarker');
    axisSubgroup = axis.append('g').attr('transform', function (d, i) {
      return buildTranslate(0, -d);
    });
    axisSubgroup.append('text').text(function (d, i) {
      // This gets us nice axis values
      return roundTo(reverseScale(d), 2);
    }).attr('text-anchor', 'right').attr('dy', -3); // remove functions if these wind up being correct

    axisSubgroup.append('line').attr('x1', function (d, i) {
      return 0;
    }).attr('y1', function (d, i) {
      return 0;
    }).attr('x2', function (d, i) {
      return gapDistance;
    }).attr('y2', function (d, i) {
      return 0;
    });
  }
  /*
  Our data is separated into groups
  Each group contains a bunch of hosts (or whatever you're measuring from)
  This draws markers that indicate where groups start and end
   The problem with drawing these are arcs it that I get less control over the css
  Style must be applied to both the line part and the rounded circle part
  Could be a proble, could be fine. Depends upon our needs.
  */


  function drawGroupMarkers(data, groupAngles) {
    var groupArc,
        prevEnd,
        start,
        end,
        byGroup,
        groupMarker,
        halfAngle,
        // we need to store the angles 
    // so we can move the label to the proper position
    // it's easier than parsing the angle from the path's "d" attribute
    angles = [],
        groupSeparator,
        theta = 0,
        prevTheta = 0;
    prevEnd = 0; // These are the lines between groups

    groupSeparator = d3_v3.svg.line().x(function (d, i) {
      var theta = correctArcAngle(d.count * arcSize);
      return (radius + 20) * Math.cos(theta);
    }).y(function (d, i) {
      var theta = correctArcAngle(d.count * arcSize);
      return (radius + 20) * Math.sin(theta);
    });
    byGroup = spiderModel.countByGroup(data, groupKey);
    groupMarker = svg.selectAll('groupMarker').data(data).enter();

    function getAngle(i) {
      if (i + 1 < groupAngles.length) {
        theta = (groupAngles[i] + groupAngles[i + 1]) / 2;
      } else {
        // this is hard coded to be half the circle
        // if we experiment with other sizes, this will have to change
        theta = (groupAngles[i] + PI) / 2;
      }

      theta = correctArcAngle(theta);
      return theta;
    }

    groupMarker.append('text').text(function (d) {
      return d.name;
    }).attr("dx", function (d, i) {
      return (radius + 10) / 2;
    }).attr("dy", function (d, i) {
      return 0 - (radius + 10);
    }).attr("text-anchor", "left").attr('class', 'groupLabel');
  }

  function removeGroupMarkers() {
    svg.selectAll('.groupLabel').remove();
  }
  /*
  These markers appear around host's slices
  This shows separation from the group
   todo: maybe put this up in plot and integrate it with the current stuff there
  it might make it more flexible for the future.
  this could really go within plot's loops
  */


  function drawHostMarkers(data) {
    var theta, sliceGroup, slope;
    var markerArc = d3_v3.svg.arc().innerRadius(0).outerRadius(radius).startAngle(0).endAngle(arcSize);

    underscore_default.a.each(data, function (group, i) {
      sliceGroup = svg.selectAll('.group#' + groupElementIds[group.name] + ' .hostGroup').data(group.data).append('g');
      sliceGroup.append('path').attr('d', markerArc).attr('class', 'hostMarker');
      sliceGroup.append('g'); // $("defs.gradCircle").children().clone().appendTo($(sliceGroup[0]))
      // d3 bug doesn't allow the colon
      // $("use[xlinkhref]").each(function(){
      //     let val = $(this).attr('xlinkhref');
      //     $(this).attr('xlink:href', val);
      //     $(this).removeAttr('xlinkhref');
      // })

      sliceGroup.append('text').text(function (d) {
        var truncateTo, fittingData; // d.name = "sometingreallyreallyreallylongsometingreallyreallyreallylong"

        fittingData = getLabelFitting(d.name, radius, arcSize);

        if (fittingData.x + fittingData.textWidth > radius) {
          truncateTo = Math.round(Math.abs(radius - fittingData.x) / fittingData.fontWidth) - 3;
          var newStr = truncateText(d.name, truncateTo);
          return newStr;
        } else {
          return d.name;
        }
      }).attr('class', function () {
        if (!labelsOn) {
          return "hidden";
        } else {
          return "hostText";
        }
      }).attr('transform', function (d, i) {
        return buildRotate(-(90 - arcSize * RAD2DEG / 2), 0, 0);
      }).attr('dx', function (d, i) {
        var text, fittingData;
        text = d.name;
        fittingData = getLabelFitting(text, radius, arcSize);
        return fittingData.x;
      }).attr('dy', function (d, i) {
        /*
        This works because of the rotation
        once we rotate, Y is now defined the movement along the Y part of the rotated line
        This basically means it defines how centered the text is within the slice
         Most importantly, rotation seems to occur after the 'dy' and 'dx' attributes are set
         The +5 probably has to do with the pixel size of the font
        */
        return arcSize / 2 + 5;
      });
    });
  }
});
;
// CONCATENATED MODULE: ./src/d3spider.js

var D3Spider = {};

D3Spider.create = function (_ref) {
  var _ref$el = _ref.el,
      el = _ref$el === void 0 ? null : _ref$el,
      _ref$name = _ref.name,
      name = _ref$name === void 0 ? "spider-graph" : _ref$name,
      _ref$data = _ref.data,
      data = _ref$data === void 0 ? [] : _ref$data,
      _ref$width = _ref.width,
      width = _ref$width === void 0 ? 410 : _ref$width,
      _ref$height = _ref.height,
      height = _ref$height === void 0 ? 510 : _ref$height,
      _ref$min = _ref.min,
      min = _ref$min === void 0 ? 0 : _ref$min,
      _ref$max = _ref.max,
      max = _ref$max === void 0 ? 100 : _ref$max;
  var spiderGraph = new spider(el, name, width, height, true);
  return spiderGraph;
};

D3Spider.plot = function (graphObj, data) {
  var min = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : 0;
  var max = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : 100;
  graphObj.plot(data, min, max);
};

D3Spider.update = function (graphObj) {
  var newData = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : [];
  graphObj.update(newData);
};

D3Spider.destroy = function (graphObj) {
  graphObj.destroy();
};

/* harmony default export */ var d3spider = (D3Spider);
// EXTERNAL MODULE: ./src/UnixSpiderGraphStyles.js
var UnixSpiderGraphStyles = __webpack_require__(4);

// CONCATENATED MODULE: ./src/RadialGraph.jsx
function RadialGraph_typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { RadialGraph_typeof = function _typeof(obj) { return typeof obj; }; } else { RadialGraph_typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return RadialGraph_typeof(obj); }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (RadialGraph_typeof(call) === "object" || typeof call === "function")) { return call; } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }

function RadialGraph_defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }







var RadialGraph_RadialGraph = /*#__PURE__*/function (_Component) {
  _inherits(RadialGraph, _Component);

  var _super = _createSuper(RadialGraph);

  function RadialGraph(props) {
    var _this;

    _classCallCheck(this, RadialGraph);

    _this = _super.call(this, props);

    RadialGraph_defineProperty(_assertThisInitialized(_this), "checkEachGroupPresent", function (data1, data2) {
      if (data1 && data1[0] && data1[0].data && data2 && data2[0] && data2[0].data) {
        if (data1[0].data.length !== data2[0].data.length) {
          return false;
        }
      } else {
        return false;
      }

      var groups1 = data1[0].data;
      var groups2 = data2[0].data;

      for (var i = 0; i < data1.length; i++) {
        if (groups1[i].name !== groups2[i].name) {
          return false;
        }
      }

      return true;
    });

    _this.myRef = /*#__PURE__*/external_react_default.a.createRef();
    _this.graphObj = undefined;
    return _this;
  }

  _createClass(RadialGraph, [{
    key: "componentDidUpdate",
    value: function componentDidUpdate(prevProps) {
      if (this.graphObj && !this.props.isIntervalUpdate) {
        d3spider.destroy(this.graphObj);
        var graphId = this.props.graphId;
        this.graphObj = undefined;
      }

      var perfData = this.props.data;

      if (!this.props.searchRunning && perfData && perfData[0] && perfData[0].data.length !== 0) {
        if (this.graphObj && this.props.isIntervalUpdate && prevProps.data && prevProps.data[0] && prevProps.data[0].data.length !== 0 && this.checkEachGroupPresent(prevProps.data, perfData)) {
          d3spider.update(this.graphObj, perfData);
        } else {
          if (this.graphObj && this.props.isIntervalUpdate && prevProps.data && prevProps.data[0] && prevProps.data[0].data.length !== 0 && !this.checkEachGroupPresent(prevProps.data, perfData)) {
            d3spider.destroy(this.graphObj);
            this.graphObj = undefined;
          }

          this.graphObj = d3spider.create({
            el: this.myRef.current,
            name: this.props.graphId
          });
          d3spider.plot(this.graphObj, this.props.data);
        }
      }
    }
  }, {
    key: "render",
    value: function render() {
      var graphId = this.props.graphId;

      if (this.props.searchRunning) {
        return /*#__PURE__*/external_react_default.a.createElement(WaitSpinner_default.a, {
          size: "medium",
          style: UnixSpiderGraphStyles["b" /* centerAlign */]
        });
      }

      var perfData = this.props.data;

      if (perfData && perfData[0] && perfData[0].data.length === 0) {
        return /*#__PURE__*/external_react_default.a.createElement(Heading_default.a, {
          style: UnixSpiderGraphStyles["b" /* centerAlign */]
        }, "No Results Found");
      }

      return /*#__PURE__*/external_react_default.a.createElement("div", {
        id: graphId,
        ref: this.myRef
      }, /*#__PURE__*/external_react_default.a.createElement("div", {
        className: "UnixSpiderGraph UnixSpiderGraph-light"
      }, /*#__PURE__*/external_react_default.a.createElement("div", {
        className: "header"
      }), /*#__PURE__*/external_react_default.a.createElement("div", {
        className: "pickerWrapper",
        style: UnixSpiderGraphStyles["m" /* noDisplay */]
      }, /*#__PURE__*/external_react_default.a.createElement("div", {
        id: "".concat(graphId, "-picker"),
        className: "picker cp-default"
      })), /*#__PURE__*/external_react_default.a.createElement("div", {
        className: "paletteWrapper"
      }, /*#__PURE__*/external_react_default.a.createElement("div", {
        id: "".concat(graphId, "-palette"),
        className: "palette cp-default"
      })), /*#__PURE__*/external_react_default.a.createElement("svg", {
        className: "UnixSpiderGraphSvg"
      }, /*#__PURE__*/external_react_default.a.createElement("defs", null, /*#__PURE__*/external_react_default.a.createElement("filter", {
        id: "".concat(graphId, "-inset-shadow"),
        width: "405%"
      }, /*#__PURE__*/external_react_default.a.createElement("feOffset", {
        dx: "0",
        dy: "0"
      }), /*#__PURE__*/external_react_default.a.createElement("feGaussianBlur", {
        stdDeviation: "2",
        result: "offset-blur"
      }), /*#__PURE__*/external_react_default.a.createElement("feComposite", {
        operator: "out",
        "in": "SourceGraphic",
        in2: "offset-blur",
        result: "inverse"
      }), /*#__PURE__*/external_react_default.a.createElement("feFlood", {
        floodColor: "black",
        floodOpacity: "1",
        result: "color"
      }), /*#__PURE__*/external_react_default.a.createElement("feComposite", {
        operator: "in",
        "in": "color",
        in2: "inverse",
        result: "shadow"
      }), /*#__PURE__*/external_react_default.a.createElement("feComposite", {
        operator: "over",
        "in": "shadow",
        in2: "SourceGraphic"
      }))))));
    }
  }]);

  return RadialGraph;
}(external_react_["Component"]);

/* harmony default export */ var src_RadialGraph = __webpack_exports__["default"] = (RadialGraph_RadialGraph);

/***/ })

}]);