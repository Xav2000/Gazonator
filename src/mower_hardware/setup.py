from setuptools import find_packages, setup

package_name = 'mower_hardware'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='xav2000',
    maintainer_email='todo@todo.com',
    description='Mower Hardware Package',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'motor_driver_node = mower_hardware.motor_driver_node:main',
        ],
    },
)
