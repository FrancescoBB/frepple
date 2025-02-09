/*
 * Copyright (C) 2017 by frePPLe bv
 *
 * This library is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Affero General Public License as published
 * by the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
 * General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

'use strict';

angular.module('operationplandetailapp').directive('shownetworkstatusDrv', shownetworkstatusDrv);

shownetworkstatusDrv.$inject = ['$window', 'gettextCatalog'];

function shownetworkstatusDrv($window, gettextCatalog) {

  var directive = {
    restrict: 'EA',
    scope: { operationplan: '=data' },
    link: linkfunc
  };
  return directive;

  function linkfunc(scope, elem, attrs) {
    var template = '<div class="card-header"><h5 class="card-title" style="text-transform: capitalize">' +
      gettextCatalog.getString("network status") +
      '</h5></div><div class="card-body">' +
      '<table class="table table-sm table-hover table-borderless"><thead><tr><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("item") + '</b>' +
      '</td><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("location") + '</b>' +
      '</td><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("onhand") + '</b>' +
      '</td><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("purchase orders") + '</b>' +
      '</td><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("distribution orders") + '</b>' +
      '</td><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("manufacturing orders") + '</b>' +
      '</td><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("overdue sales orders") + '</b>' +
      '</td><td>' +
      '<b style="text-transform: capitalize;">' + gettextCatalog.getString("sales orders") + '</b>' +
      '</td></tr></thead>' +
      '<tbody></tbody>' +
      '</table></div>';

    scope.$watchGroup(['operationplan.id', 'operationplan.network.length'], function (newValue, oldValue) {
      angular.element(document).find('#attributes-networkstatus').empty().append(template);
      var rows = '<tr><td colspan="8">' + gettextCatalog.getString('no network information') + '</td></tr>';

      if (typeof scope.operationplan !== 'undefined') {
        if (scope.operationplan.hasOwnProperty('network')) {
          rows = '';
          angular.forEach(scope.operationplan.network, function (thenetwork) {
            rows += '<tr><td>' + $.jgrid.htmlEncode(thenetwork[0])
              + "<a href=\"" + url_prefix + "/detail/input/item/" + admin_escape(thenetwork[0])
              + "/\" onclick='event.stopPropagation()'><span class='ps-2 fa fa-caret-right'></span></a>";
            if (thenetwork[1] === true) {
              rows += '<small>' + gettextCatalog.getString('superseded') + '</small>';
            }
            rows += '</td><td>'
              + $.jgrid.htmlEncode(thenetwork[2])
              + "<a href=\"" + url_prefix + "/detail/input/location/" + admin_escape(thenetwork[2])
              + "/\" onclick='event.stopPropagation()'><span class='ps-2 fa fa-caret-right'></span></a>"
              + '</td><td>'
              + grid.formatNumber(thenetwork[3]) + '</td><td>'
              + grid.formatNumber(thenetwork[4]) + '</td><td>'
              + grid.formatNumber(thenetwork[5]) + '</td><td>'
              + grid.formatNumber(thenetwork[6]) + '</td><td>'
              + grid.formatNumber(thenetwork[7]) + '</td><td>'
              + grid.formatNumber(thenetwork[8]) + '</td></tr>';
          });
        }
      }
      angular.element(document).find('#attributes-networkstatus tbody').append(rows);
    }); //watch end

  } //link end
} //directive end
