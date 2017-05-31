/*
Copyright (c) 2016 Andre Santos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/

/*
The idea is to have modular components, and this script will be the glue between them.

This script should be included first, to define window.App.
Other modules register themselves on window.App.
When the document is ready, grab window.App and delete the global.

Other modules will essentially use Backbone.Events to communicate.

This script creates the views with the document nodes, and the models from data.
*/

(function () {
    "use strict";

    var App = window.App = {
        Views: {},
        Models: {},
        board: null, // current view
        rules: null,
        packages: null,
        summary: null,
        violations: null
    };

    $(document).ready(function () {
        delete window.App;

        App.rules = new App.Models.RuleCollection();
        App.packages = new App.Models.PackageCollection();
        App.summary = new App.Models.Summary();
        App.violations = new App.Models.ViolationCollection();

        $(window).resize(_.debounce(onResize, 100));

        bootstrapViews();
        Backbone.history.start();
        preloadData();
    });



    function preloadData() {
        App.rules.fetch();
        App.packages.fetch();
        App.summary.fetch();
    }


    function bootstrapViews() {
        App.navigation = new App.Views.NavigationMenu({
            el: $("#app-header > .navigation-menu")
        });
        App.preloader = new App.Views.Preloader({
            el: $("#preloader"),
            model: App.summary,
            packages: App.packages,
            rules: App.rules,
            violations: App.violations
        });
        App.dashboard = new App.Views.Dashboard({
            el: $("#dashboard"),
            model: App.summary
        });
        App.packageBoard = new App.Views.PackageBoard({
            el: $("#package-board"),
            collection: App.packages,
            rules: App.rules,
            router: App.router
        });
        App.issueBoard = new App.Views.IssueBoard({
            el: $("#issue-board"),
            collection: new App.Models.ViolationCollection(),
            packages: App.packages,
            rules: App.rules,
            router: App.router
        });
        App.rosBoard = new App.Views.RosBoard({
            el: $("#ros-board"),
            collection: new App.Models.ConfigurationCollection(),
            packages: App.packages,
            router: App.router
        });
        App.helpBoard = new App.Views.HelpBoard({
            el: $("#help-board")
        });
        // TODO: use a system other than these "public variables".
        App.packageBoard.publicVars.issues = App.issueBoard.publicVars;
        // Hide everything. Each route shows its view.
        App.dashboard.hide();
        App.packageBoard.hide();
        App.issueBoard.hide();
        App.rosBoard.hide();
        App.helpBoard.hide();
    }


    function onResize(event) {
        if (App.board != null) {
            App.board.onResize(event);
        }
    }
})();
