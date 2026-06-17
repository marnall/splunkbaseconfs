require.config({"paths":{"react-dom":"/static/app/getwatchlist/js/react-dom.js?v=0316bb9fe8871c426983","about":"/static/app/getwatchlist/js/about.js?v=cbcf83b943da2f881c4b","react":"/static/app/getwatchlist/js/react.js?v=302f2a1255d084a04f21"},"shim":{"react-dom":{"exports":"react-dom"},"about":{"exports":["about"]},"react":{"exports":"react"}}});
                require([
                        "splunkjs/ready!",
                        "splunkjs/mvc/simplexml/ready!",
                        "splunkjs/mvc/utils",
                        "react-dom", "about", "react"
                    ], function (mvc,
                                 ignored,
                                 splunkjsUtils,
                                 reactdom, about, react
                    ) {
                        let default_tokens = mvc.Components.get("default"), submitted_tokens = mvc.Components.get("submitted");
                        let splunk_theme_name = window.__splunk_page_theme__ ? window.__splunk_page_theme__ : window.DASHBOARD_THEME ? window.DASHBOARD_THEME : "default";
                        let myObjects = $("#root").each((k, v)=>{
                            const root = reactdom.createRoot(
                                v, 
                                {identifierPrefix: "about"});
                            const react_app = react.createElement(about.default, {
                                    splunkjs: mvc,
                                    mvc: mvc,
                                    utils: splunkjsUtils,
                                    app_context: "getwatchlist",
                                    family: splunk_theme_name,
                                    color_scheme: splunk_theme_name,
                                    ...$(v).data(),
                                    default_tokens, submitted_tokens,
                                    
                                    });
                            
                            root.render(react_app);
                          }); //end iterator
                       });
                