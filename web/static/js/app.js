var dazzarApp = angular.module('dazzarApp', []);

dazzarApp.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{a');
    $interpolateProvider.endSymbol('a}');
});

dazzarApp.controller('NicknameController', ['$scope', '$http', '$window', function ($scope, $http, $window) {
    $scope.nickname = '';
    $scope.message = '';

    $scope.validate_nickname = function() {
        $http({
            method: 'POST',
            url: '/api/nickname/select',
            data: {
                'nickname': $scope.nickname
            }
        }).then(function successCallback(response) {
            console.log(response.data);
            if (response.data['status'] == 'ok') {
                $window.location.href = '/';
            } else {
                $scope.message = response.data['message']
            }
        }, function errorCallback(response) {
            console.log(response)
        });
    }
}]);

dazzarApp.controller('QueueController', ['$scope', '$http', '$interval', '$window', function ($scope, $http, $interval, $window) {
    $scope.queue_details = {
        is_open: false,
        user: {
            in_queue: false,
            game: null
        },
        queues: {
            high: 0,
            medium: 0,
            low: 0
        }
    };
    $scope.modes = {
        ap: true,
        rd: true,
        cd: true
    };

    $scope.open_close_ladder = function(open_close) {
        $http({
            method: 'GET',
            url: '/api/ladder/queue/change',
            params: {
                'open': open_close
            }
        }).then(function successCallback(response) {
            $scope.queue_details = response.data
        }, function errorCallback(response) {
            console.log(response)
        });
    };

    $scope.refresh_queue_details = function() {
        $http({
            method: 'GET',
            url: '/api/ladder/queue/details'
        }).then(function successCallback(response) {
            $scope.queue_details = response.data
            $scope.redirect_if_game();
        }, function errorCallback(response) {
            console.log(response)
        });
    };

    $scope.in_out_queue = function(in_out) {
        $http({
            method: 'POST',
            url: '/api/ladder/queue/in_out',
            headers: {
                'Content-Type': 'application/json'
            },
            data: {
                in: in_out,
                modes: $scope.modes
            }
        }).then(function successCallback(response) {
            $scope.queue_details = response.data
            $scope.redirect_if_game();
        }, function errorCallback(response) {
            console.log(response)
        });
    };

    $scope.redirect_if_game = function() {
        if ($scope.queue_details.user.game != null) {
            $window.location.href = '/ladder/match/' + $scope.queue_details.user.game;
        }
    }

    $scope.refresh_queue_details()
    $interval($scope.refresh_queue_details, 15000);
}]);
