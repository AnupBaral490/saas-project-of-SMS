/**
 * Parent Dashboard Charts
 * Handles attendance and performance chart rendering
 */

function initializeParentDashboardCharts(childrenData) {
    if (!childrenData || childrenData.length === 0) {
        return;
    }

    childrenData.forEach(function(childData, index) {
        var chartIndex = index + 1;
        
        // Initialize Attendance Chart
        initializeAttendanceChart(chartIndex, childData);
        
        // Initialize Performance Chart
        if (childData.subjects && childData.subjects.length > 0) {
            initializePerformanceChart(chartIndex, childData);
        }
    });
}

function initializeAttendanceChart(chartIndex, childData) {
    var attendanceCtx = document.getElementById('attendanceChart' + chartIndex);
    if (!attendanceCtx) return;
    
    var absentSessions = childData.totalSessions - childData.presentSessions;
    
    new Chart(attendanceCtx, {
        type: 'doughnut',
        data: {
            labels: ['Present', 'Absent'],
            datasets: [{
                data: [childData.presentSessions, absentSessions],
                backgroundColor: [
                    'rgba(28, 200, 138, 0.9)',
                    'rgba(231, 74, 59, 0.9)'
                ],
                borderColor: '#fff',
                borderWidth: 3,
                hoverOffset: 15
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: {
                            size: 13,
                            weight: '500'
                        },
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function(context) {
                            var label = context.label || '';
                            var value = context.parsed || 0;
                            var total = childData.totalSessions;
                            var percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return label + ': ' + value + ' sessions (' + percentage + '%)';
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
}

function initializePerformanceChart(chartIndex, childData) {
    var performanceCtx = document.getElementById('performanceChart' + chartIndex);
    if (!performanceCtx) return;
    
    var subjectNames = childData.subjects.map(function(s) { return s.name; });
    var subjectPercentages = childData.subjects.map(function(s) { return s.percentage; });
    var subjectColors = childData.subjects.map(function(s) {
        if (s.percentage >= 85) return 'rgba(28, 200, 138, 0.9)';
        if (s.percentage >= 70) return 'rgba(54, 185, 204, 0.9)';
        if (s.percentage >= 60) return 'rgba(246, 194, 62, 0.9)';
        return 'rgba(231, 74, 59, 0.9)';
    });
    
    new Chart(performanceCtx, {
        type: 'bar',
        data: {
            labels: subjectNames,
            datasets: [{
                label: 'Performance',
                data: subjectPercentages,
                backgroundColor: subjectColors,
                borderRadius: 8,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: 'rgba(0,0,0,0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        },
                        font: {
                            size: 12
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function(context) {
                            var value = context.parsed.y;
                            var grade = childData.subjects[context.dataIndex].grade;
                            return 'Score: ' + value + '% | Grade: ' + grade;
                        }
                    }
                }
            },
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Read data from JSON script tag
    var dataElement = document.getElementById('parent-dashboard-data');
    if (dataElement) {
        try {
            var parentDashboardData = JSON.parse(dataElement.textContent);
            initializeParentDashboardCharts(parentDashboardData);
        } catch (e) {
            console.error('Error parsing parent dashboard data:', e);
        }
    }
});
