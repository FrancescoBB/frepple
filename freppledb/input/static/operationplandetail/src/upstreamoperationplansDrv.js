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

angular.module('operationplandetailapp').directive('showupstreamoperationplansDrv', showupstreamoperationplansDrv);

showupstreamoperationplansDrv.$inject = ['$window', 'gettextCatalog'];

function showupstreamoperationplansDrv($window, gettextCatalog) {

	var directive = {
		restrict: 'EA',
		scope: { operationplan: '=data' },
		templateUrl: '/static/operationplandetail/upstreamoperationplans.html',
		link: linkfunc
	};
	return directive;

	function linkfunc(scope, elem, attrs) {

		function expandOrCollapse(i) {
			// 0: collapsed, 1: expanded, 2: hidden, 3: leaf
			var j = i + 1;
			var mylevel = scope.operationplan.upstreamoperationplans[i][0];
			if (scope.operationplan.upstreamoperationplans[i][11] == 0)
				scope.operationplan.upstreamoperationplans[i][11] = 1;
			else
				scope.operationplan.upstreamoperationplans[i][11] = 0;
			while (j < scope.operationplan.upstreamoperationplans.length) {
				if (scope.operationplan.upstreamoperationplans[j][0] <= mylevel)
					break;
				else if (scope.operationplan.upstreamoperationplans[j][0] > mylevel + 1
					|| scope.operationplan.upstreamoperationplans[i][11] == 0)
					scope.operationplan.upstreamoperationplans[j][11] = 2;
				else if (j == scope.operationplan.upstreamoperationplans.length - 1 ||
					scope.operationplan.upstreamoperationplans[j][0] >= scope.operationplan.upstreamoperationplans[j + 1][0])
					scope.operationplan.upstreamoperationplans[j][11] = 3;
				else if (scope.operationplan.upstreamoperationplans[j][0] == mylevel + 1
					&& scope.operationplan.upstreamoperationplans[i][11] == 1)
					scope.operationplan.upstreamoperationplans[j][11] = 0;
				++j;
			}
		}
		scope.expandOrCollapse = expandOrCollapse;

		scope.url_prefix = url_prefix;
	} //link end
} //directive end
