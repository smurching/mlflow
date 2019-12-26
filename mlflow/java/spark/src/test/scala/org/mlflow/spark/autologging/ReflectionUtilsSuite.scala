package org.mlflow.spark.autologging

import java.io.File
import java.nio.file.{Files, Path, Paths}
import java.util.UUID

import org.apache.spark.mlflow.MlflowSparkAutologgingTestUtils
import org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd
import org.apache.spark.sql.types.{IntegerType, StringType, StructField, StructType}
import org.apache.spark.sql.{Row, SparkSession}
import org.mockito.Matchers.any
import org.mockito.Mockito._
import org.scalatest.{BeforeAndAfterAll, BeforeAndAfterEach, FunSuite, Matchers}

object TestObject {

}

abstract class TestAbstractClass {
  def addNumbers(x: Int, y: Int): Int = x + y
}

class RealClass extends TestAbstractClass {
  private val myField: String = "myCoolVal"
  def subclassMethod(x: Int): Int = x * x
}

class ReflectionUtilsSuite extends FunSuite with Matchers {

  test("Can use reflection to determine if object is instance of class") {
    val obj = new RealClass()
    assert(ReflectionUtils.isInstanceOf(obj, "org.mlflow.spark.autologging.TestAbstractClass"))
    assert(ReflectionUtils.isInstanceOf(obj, "org.mlflow.spark.autologging.RealClass"))
  }

  test("Can get private field of an object via reflection") {
    val obj = new RealClass()
    val field = ReflectionUtils.getField(obj, "myField").asInstanceOf[String]
    assert(field == "myCoolVal")
  }

  test("Can call methods via reflection") {
    val obj = new RealClass()
    val args0: Seq[Object] = Seq[Integer](3)
    val res0 = ReflectionUtils.callMethod(obj, "subclassMethod", args0).asInstanceOf[Int]
    assert(res0 == 9)
  }



}
